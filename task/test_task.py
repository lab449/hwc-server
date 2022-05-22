import unittest
import task


class TestTask(unittest.TestCase):
    def setUp(self):
        pass

    def testCases(self):
        stask = task.Task('server_task_data/test_task.json')
        for i in range(4):
            number = stask.generate_case_number()
            print("Generated case number: {:d}".format(number))
            self.assertIsInstance(number, int)
            case = stask.get_case(number)
            self.assertIsInstance(case.jsonify(), dict)
            print("Civen case: {:s}".format(str(case)) )
            self.assertIsInstance(case, task.Case)
            case_with_answers = case.jsonify(True)
            # print(case_with_answers)
            good_score = case.check(case_with_answers['answers'])
            self.assertIsInstance(good_score, task.CaseScore)
            self.assertEqual(good_score.total, 1.0)
            fk = list(case_with_answers['answers'].keys())[0]
            case_with_answers['answers'][fk] = -1e+6
            bad_score = case.check(case_with_answers['answers'])
            self.assertIsInstance(bad_score, task.CaseScore)
            self.assertEqual(bad_score.total, 0.0)
            


if __name__ == '__main__':
    unittest.main()