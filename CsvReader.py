import csv

def read_csv_without_headers(file_path):
    csvFile = []
    with open(file_path, 'r', newline='') as file:
        csv_reader = csvFile.reader(file)
        headers = next(csv_reader)  # Skip headers
        for row in csv_reader:
            csvFile.append(row)
    return csvFile