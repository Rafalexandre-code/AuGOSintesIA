from pymongo import MongoClient
import json
import argparse
import sys


def parse_arguments(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', help='Database name.', default='UV_data')
    parser.add_argument('--json_file', help='json file path.', default='20210709_150145_Ag_01.json')
    parser.add_argument('--element', help='chemical element.', default='Ag')
    parser.add_argument('--cycle_number', help='cycle_number.', default='01')

    return parser.parse_args(argv)


def main(args):
    print(args)
    client = MongoClient('mongodb://localhost:27017/')
    db_cm = client[args.db]
    
    print(db_cm.UV_info)

    data_dir, data_file = args.json_file[:8], args.json_file[8:]

    with open(data_dir+data_file, 'r') as data:
        data_json = json.load(data)
        data_json["Element"]=args.element
        data_json["Cycle_number"]=args.cycle_number
        # add later
    
    result = db_cm.UV_info.insert_one(data_json)
    print("MongoDB: Inserted JSON file!")


if __name__ == '__main__':
    main(parse_arguments(sys.argv[1:]))
