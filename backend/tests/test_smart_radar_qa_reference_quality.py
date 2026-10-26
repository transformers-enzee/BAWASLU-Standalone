"""No-inference validation of v2 reference-quality gates."""
from app.smart_radar_qa_reference_quality import select_reference_v2
REC={"qa_id":"QA-50","cohort":"development","source_hash":"h","source_url":"https://example.test/target"}
EX=[{"qa_id":f"QA-{n}","cohort":"exemplar","source_hash":str(n),
     "source_url":f"https://example.test/{n}","gold_category":cat}
    for n,cat in [(1,"Disputes / Legal"),(2,"Allegations / Violations"),(3,"Disputes / Legal")]]
class FakeDB:
    def __init__(self,rows):self.rows=rows
    def execute(self,query,params):return self
    def mappings(self):return self
    def all(self):return self.rows
def row(n,cat,sim):
    return {"qa_id":f"QA-{n}","shahrin_category":cat,"similarity":sim,
            "excerpt":"Example content with actual context."}
def test_conflicting_categories_abstain():
    refs,reason=select_reference_v2(FakeDB([row(1,"Disputes / Legal",.47),
        row(2,"Allegations / Violations",.42)]),REC,EX)
    assert refs==[] and reason=="category_conflict"
def test_weak_neighbors_abstain():
    refs,reason=select_reference_v2(FakeDB([row(1,"Disputes / Legal",.21)]),REC,EX)
    assert refs==[] and reason=="weak_similarity"
def test_qualified_examples_use_consistent_category():
    refs,reason=select_reference_v2(FakeDB([
        row(1,"Disputes / Legal",.44),row(3,"Disputes / Legal",.34),
        row(2,"Allegations / Violations",.19)]),REC,EX)
    assert reason=="qualified" and len(refs)==2
    assert all(x["human_primary_category"]=="Disputes / Legal" for x in refs)
def test_no_target_label_exposed():
    refs,reason=select_reference_v2(FakeDB([row(50,"Allegations / Violations",.6)]),REC,EX)
    assert refs==[] and reason=="no_reliable_reference"
