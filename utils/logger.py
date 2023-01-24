import csv

class Logger:
    def __init__(self) -> None:
        self.file = open('log.csv', 'a')
        self.logWriter = csv.writer(self.file)
        
    def write(self, row):
        self.logWriter.writerow(row)
        
    def close(self):
        self.file.close()