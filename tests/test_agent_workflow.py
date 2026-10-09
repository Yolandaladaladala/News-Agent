import unittest
from agent_workflow import canonical_url,rank_candidates,parse_edit_request,apply_editorial_operations

class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{"news_id":1,"title":"Thai auto finance","url":"https://example.com/a?utm_source=x","score":90,"status":"已核验"},
                   {"news_id":2,"title":"US auto loans","url":"https://example.com/b","score":85,"status":"待核验"},
                   {"news_id":3,"title":"Japanese production","url":"https://example.com/c","score":75,"status":"已核验"}]
    def test_url_tracking(self):
        self.assertEqual(canonical_url(self.rows[0]["url"]),"https://example.com/a")
    def test_shortlist(self):
        top,reserve=rank_candidates(self.rows,2)
        self.assertEqual(len(top),2)
        self.assertEqual(len(reserve),1)
    def test_delete_preserves_other_rows(self):
        result=parse_edit_request("删除 1、3",self.rows)
        self.assertEqual(result["action"],"delete")
        self.assertEqual([r["news_id"] for r in result["rows"]],[2])
    def test_unknown_id_is_rejected(self):
        self.assertEqual(parse_edit_request("删除 99",self.rows)["action"],"error")
    def test_unrestricted_text_requires_model(self):
        self.assertEqual(parse_edit_request("补充泰国央行新闻",self.rows)["action"],"needs_ai")
    def test_structured_edit(self):
        rows=apply_editorial_operations(self.rows,[{"action":"update","news_id":2,"fields":{"title":"Updated"}}])
        self.assertEqual(rows[1]["title"],"Updated")
        self.assertEqual(self.rows[1]["title"],"US auto loans")
    def test_reject_unsupported_field(self):
        with self.assertRaises(ValueError):
            apply_editorial_operations(self.rows,[{"action":"update","news_id":1,"fields":{"status":"已核验"}}])

if __name__=="__main__":unittest.main()
