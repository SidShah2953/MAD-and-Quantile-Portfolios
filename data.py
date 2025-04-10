from scripts.data.collection import collect_data
from scripts.data.processing import process_data

if __name__ == '__main__':
    collect_data()
    process_data()
    print('Data collection and processing completed.')