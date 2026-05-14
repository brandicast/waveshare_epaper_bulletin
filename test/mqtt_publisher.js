#!/usr/bin/env node

/**
 * E-Paper Bulletin Board - MQTT Raw Pixel Data Publisher
 * 
 * Sends raw pixel data (800x480 monochrome) to MQTT broker
 * 
 * Installation:
 *   npm install mqtt jimp
 * 
 * Usage:
 *   node mqtt_publisher.js <image_path> [mqtt_server] [mqtt_port] [topic]
 * 
 * Examples:
 *   node mqtt_publisher.js test_image.png
 *   node mqtt_publisher.js test_image.png 172.28.248.138 1883 epaper/bulletin
 *   node mqtt_publisher.js --pattern checkerboard
 *   node mqtt_publisher.js --pattern text "Hello World"
 */

const mqtt = require('mqtt');
const Jimp = require('jimp');
const fs = require('fs');
const path = require('path');

// Configuration
const config = {
    width: 800,
    height: 480,
    server: process.env.MQTT_SERVER || '172.28.248.138',
    port: parseInt(process.env.MQTT_PORT || '1883'),
    topic: process.env.MQTT_TOPIC || 'epaper/bulletin',
};

// Parse command line arguments
const args = process.argv.slice(2);
let imagePath = null;
let patternType = null;
let patternText = null;

for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--pattern')) {
        patternType = args[i + 1];
        if (args[i + 2] && !args[i + 2].startsWith('-')) {
            patternText = args[i + 2];
            i += 2;
        } else {
            i += 1;
        }
    } else if (!args[i].startsWith('-')) {
        if (imagePath === null) {
            imagePath = args[i];
        } else if (!isNaN(args[i])) {
            if (config.server === '172.28.248.138') {
                config.server = args[i];
            } else if (config.port === 1883) {
                config.port = parseInt(args[i]);
            }
        } else {
            if (config.server === '172.28.248.138') {
                config.server = args[i];
            } else {
                config.topic = args[i];
            }
        }
    }
}

console.log('E-Paper Bulletin Board - MQTT Publisher');
console.log('=========================================');
console.log(`Display: ${config.width}x${config.height} monochrome`);
console.log(`MQTT Server: ${config.server}:${config.port}`);
console.log(`Topic: ${config.topic}`);
console.log('');

/**
 * Convert image to raw pixel data (monochrome, 1-bit per pixel)
 * Returns Buffer of 48,000 bytes
 */
async function imageToRawPixels(imagePath) {
    try {
        console.log(`Loading image: ${imagePath}`);

        // Read image
        const image = await Jimp.read(imagePath);

        // Resize to target dimensions
        image.resize(config.width, config.height);

        // Convert to grayscale
        image.grayscale();

        // Convert to 1-bit (monochrome) and create raw data
        const rawData = new Uint8Array(48000); // 800 * 480 / 8
        let byteIndex = 0;
        let bitIndex = 0;

        for (let y = 0; y < config.height; y++) {
            for (let x = 0; x < config.width; x++) {
                // Get pixel color (0-255)
                const pixelColor = Jimp.intToRGBA(image.getPixelColor(x, y));

                // Convert to 1-bit (threshold at 128)
                // 1 = black, 0 = white
                const bit = pixelColor.r > 128 ? 0 : 1;

                // Pack bits into bytes (MSB first)
                rawData[byteIndex] |= (bit << (7 - bitIndex));

                bitIndex++;
                if (bitIndex === 8) {
                    bitIndex = 0;
                    byteIndex++;
                }
            }
        }

        console.log(`Converted image to ${rawData.length} bytes`);
        return Buffer.from(rawData);
    } catch (error) {
        console.error(`Error loading image: ${error.message}`);
        throw error;
    }
}

/**
 * Create pattern-based raw pixel data
 */
function createPattern(patternType, text) {
    const rawData = new Uint8Array(48000);

    console.log(`Creating pattern: ${patternType}`);

    switch (patternType) {
        case 'checkerboard':
            // Checkerboard pattern
            for (let y = 0; y < config.height; y++) {
                for (let x = 0; x < config.width; x++) {
                    const byteIndex = Math.floor((y * config.width + x) / 8);
                    const bitIndex = 7 - ((y * config.width + x) % 8);

                    // Alternate black/white every 20 pixels
                    const isBlack = ((Math.floor(x / 20) + Math.floor(y / 20)) % 2) === 0;
                    if (isBlack) {
                        rawData[byteIndex] |= (1 << bitIndex);
                    }
                }
            }
            break;

        case 'gradient':
            // Horizontal gradient
            for (let y = 0; y < config.height; y++) {
                for (let x = 0; x < config.width; x++) {
                    const byteIndex = Math.floor((y * config.width + x) / 8);
                    const bitIndex = 7 - ((y * config.width + x) % 8);

                    // Gradient from white (left) to black (right)
                    const threshold = (x / config.width) * 255;
                    if (128 > threshold) {
                        rawData[byteIndex] |= (1 << bitIndex);
                    }
                }
            }
            break;

        case 'white':
            // All white (0x00)
            rawData.fill(0x00);
            break;

        case 'black':
            // All black (0xFF)
            rawData.fill(0xFF);
            break;

        case 'border':
            // White background with black border
            rawData.fill(0x00); // White

            const borderWidth = 20;
            for (let y = 0; y < config.height; y++) {
                for (let x = 0; x < config.width; x++) {
                    if (x < borderWidth || x >= config.width - borderWidth ||
                        y < borderWidth || y >= config.height - borderWidth) {
                        const byteIndex = Math.floor((y * config.width + x) / 8);
                        const bitIndex = 7 - ((y * config.width + x) % 8);
                        rawData[byteIndex] |= (1 << bitIndex);
                    }
                }
            }
            break;

        case 'text':
            // White background with text message
            rawData.fill(0x00); // White

            if (text) {
                console.log(`Adding text: "${text}"`);
                // Simple text pattern (centers a message)
                // This is a simple implementation - just marks some pixels as black
                const textX = 50;
                const textY = 200;
                const charWidth = 20;

                for (let i = 0; i < Math.min(text.length, 30); i++) {
                    for (let j = 0; j < charWidth; j++) {
                        for (let k = 0; k < 30; k++) {
                            const x = textX + i * charWidth + j;
                            const y = textY + k;

                            if (x < config.width && y < config.height) {
                                const byteIndex = Math.floor((y * config.width + x) / 8);
                                const bitIndex = 7 - ((y * config.width + x) % 8);
                                rawData[byteIndex] |= (1 << bitIndex);
                            }
                        }
                    }
                }
            }
            break;

        default:
            console.warn(`Unknown pattern: ${patternType}, using white`);
            rawData.fill(0x00);
    }

    console.log(`Created pattern: ${rawData.length} bytes`);
    return Buffer.from(rawData);
}

/**
 * Publish pixel data to MQTT
 */
function publishToMQTT(pixelBuffer) {
    return new Promise((resolve, reject) => {
        const mqttUrl = `mqtt://${config.server}:${config.port}`;
        console.log(`\nConnecting to MQTT: ${mqttUrl}`);

        const client = mqtt.connect(mqttUrl, {
            reconnectPeriod: 5000,
            connectTimeout: 10000,
        });

        client.on('connect', () => {
            console.log('Connected to MQTT broker');
            console.log(`Publishing ${pixelBuffer.length} bytes to topic: ${config.topic}`);

            client.publish(config.topic, pixelBuffer, { qos: 0 }, (error) => {
                if (error) {
                    console.error(`Publish error: ${error.message}`);
                    client.end();
                    reject(error);
                } else {
                    console.log('✓ Pixel data published successfully');
                    console.log(`\nImage sent to Pico at ${config.server}`);
                    client.end();
                    resolve();
                }
            });
        });

        client.on('error', (error) => {
            console.error(`MQTT error: ${error.message}`);
            client.end();
            reject(error);
        });

        client.on('offline', () => {
            console.warn('MQTT client offline');
        });
    });
}

/**
 * Main function
 */
async function main() {
    try {
        let pixelBuffer;

        if (patternType) {
            // Create pattern
            pixelBuffer = createPattern(patternType, patternText);
        } else if (imagePath) {
            // Convert image file
            pixelBuffer = await imageToRawPixels(imagePath);
        } else {
            // Show help and create default pattern
            console.log('Usage:');
            console.log('  node mqtt_publisher.js <image_path> [server] [port] [topic]');
            console.log('  node mqtt_publisher.js --pattern <pattern> [text]');
            console.log('');
            console.log('Patterns:');
            console.log('  checkerboard - Black and white checkerboard');
            console.log('  gradient     - Horizontal gradient');
            console.log('  white        - All white (blank)');
            console.log('  black        - All black');
            console.log('  border       - Border around white background');
            console.log('  text <msg>   - Text message on white background');
            console.log('');
            console.log('Examples:');
            console.log('  node mqtt_publisher.js image.png');
            console.log('  node mqtt_publisher.js --pattern checkerboard');
            console.log('  node mqtt_publisher.js --pattern text "Hello Pico"');
            console.log('');
            console.log('Using default pattern: checkerboard');
            pixelBuffer = createPattern('checkerboard');
        }

        // Publish to MQTT
        await publishToMQTT(pixelBuffer);
        process.exit(0);

    } catch (error) {
        console.error(`\n✗ Error: ${error.message}`);
        process.exit(1);
    }
}

// Run main
main();
