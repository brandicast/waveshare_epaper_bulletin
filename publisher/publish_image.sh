echo Publishing $1
 
python main.py --image $1 --host 192.168.0.96 --port 1883  --topic epaper/bulletin/binary 
