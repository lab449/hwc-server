import json
import random
import argparse

parser = argparse.ArgumentParser(description='Random case selection programm')
parser.add_argument('--input', '-in', type=str, help='Input json file')
parser.add_argument('--num_cases', '-n', type=int, help='Count of new answers expected in task')

args = parser.parse_args()

def main():
    with open(args.input, 'r') as f:
        data = json.load(f)
    
    cases = data['cases']
    answer_list_size = []
    for c in cases:
        answers_list = list(c['answers'].keys())
        random_cases = random.choices(population=answers_list, k=args.num_cases)
        new_ans = {key: c['answers'][key] for key in random_cases}
        c['answers'] = new_ans
        answer_list_size.append([len(answers_list), len(random_cases)])
    
    print(answer_list_size)


if __name__ == "__main__":
    main()