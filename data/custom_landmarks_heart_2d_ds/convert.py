import os
files = os.listdir('.')

for f in files:
	if '.txt' not in f:
		continue
	with open(f,'r') as file:
		line = file.readline()
		temp = line.split(',')
		x = int(temp[0])
		#print(x)
		y = int(temp[1])
		new_x = round(x*.75)
		new_y = round(y*.75)
		new_line = str(new_x) + ',' + str(new_y)
	with open(f,'w') as file:
		file.seek(0)
		file.write(new_line)		
