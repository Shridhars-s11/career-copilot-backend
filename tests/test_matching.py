import pytest
from app.tools.matching import cosine_similarity, keyword_score
 
 
def test_cosine_similarity_identical_vectors_is_one():
    v = [1.0, 0.5, 0.2]
    assert cosine_similarity(v, v) == pytest.approx(1.0)
 
 
def test_cosine_similarity_orthogonal_vectors_is_zero():
    a = [1.0, 0.0]
    b = [0.0, 1.0]
    assert cosine_similarity(a, b) == pytest.approx(0.0)
 
 
def test_cosine_similarity_opposite_vectors_is_negative_one():
    a = [1.0, 0.0]
    b = [-1.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(-1.0)
 
 
def test_keyword_score_full_match_is_one():
    description = "We need a Python developer with FastAPI and Docker experience"
    skills = ["Python", "FastAPI", "Docker"]
    assert keyword_score(description, skills) == pytest.approx(1.0)
 
 
def test_keyword_score_no_match_is_zero():
    description = "We need a sales executive with retail experience"
    skills = ["Python", "FastAPI", "Docker"]
    assert keyword_score(description, skills) == pytest.approx(0.0)
 
 
def test_keyword_score_partial_match():
    description = "We need a Python developer"
    skills = ["Python", "FastAPI", "Docker"]
    assert keyword_score(description, skills) == pytest.approx(1 / 3)
 
 
def test_keyword_score_is_case_insensitive():
    description = "we need a PYTHON developer"
    skills = ["Python"]
    assert keyword_score(description, skills) == pytest.approx(1.0)