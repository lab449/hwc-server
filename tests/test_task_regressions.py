import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from task.task import Task, ArrayAnswer, NumberAnswer, IntegerAnswer


class TaskRegressions(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'task.json'
        self.path.write_text(json.dumps({'cases':[{'parameters':{'case':i},'answers':{},'files':[]} for i in range(3)]}))
        self.task=Task(str(self.path))
    def tearDown(self):self.tmp.cleanup()
    def test_zero_and_last_variant(self):
        self.assertEqual(self.task.get_case(0).jsonify()['parameters']['case'],0)
        self.assertEqual(self.task.get_case(2).jsonify()['parameters']['case'],2)
    def test_generated_variants_are_loadable(self):
        np.random.seed(7)
        numbers=[self.task.generate_case_number() for _ in range(100)]
        self.assertEqual(set(numbers),{0,1,2})
        for n in numbers:self.task.get_case(n)
    def test_out_of_bounds_and_invalid_types(self):
        for n in [-1,3,True,1.5,'0',None]:
            with self.subTest(n=n),self.assertRaises((ValueError,IndexError,TypeError)):self.task.get_case(n)
    def test_malformed_numeric_answers(self):
        array=ArrayAnswer({'inst':'list','score':1,'valid_range':.01,'true_value':[1,2]})
        for v in [['1','2'],[None,2],[[1],[2,3]],[float('inf'),2],[True,2],[1,False]]:
            with self.subTest(v=v):self.assertIsNone(array.check(v))
        for klass,kind in [(NumberAnswer,'float'),(IntegerAnswer,'int')]:
            answer=klass({'inst':kind,'score':1,'valid_range':.01,'true_value':1})
            self.assertIsNone(answer.check(True))
            self.assertIn(answer.check(10**500), (None, 0))


if __name__=='__main__':unittest.main(verbosity=2)
