import unittest
from summary import summarise

class SummaryTests(unittest.TestCase):
    def test_counts_and_order(self):
        tasks = [{'title':'Second', 'status':'pending'}, {'title':'Complete', 'status':'done'}, {'title':'First', 'status':'pending'}]
        self.assertEqual(summarise(tasks), {'done':1, 'pending':2, 'next_actions':['Second','First']})

    def test_empty_list(self):
        self.assertEqual(summarise([]), {'done':0, 'pending':0, 'next_actions':[]})

    def test_invalid_records(self):
        for value in [None, {}, [None], [{'title':'', 'status':'done'}], [{'title':'Task', 'status':'unknown'}]]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarise(value)

if __name__ == '__main__':
    unittest.main()
