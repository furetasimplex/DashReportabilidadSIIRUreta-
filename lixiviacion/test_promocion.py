import pytest
from .promote_estado_dev import functional_hash, split_definition


def test_literal_body_preserved_with_strings_comments_and_test_references():
    body = "(@fecha date) RETURNS TABLE AS RETURN (SELECT 'test' AS valor /* CASE intacto */)"
    original = 'CREATE OR ALTER FUNCTION [dbo].[test]'+body
    promoted = 'CREATE FUNCTION dbo.oficial'+split_definition(original, 'dbo.test')
    assert promoted == 'CREATE FUNCTION dbo.oficial'+body
    assert functional_hash(original, 'dbo.test') == functional_hash(promoted, 'dbo.oficial')
    assert functional_hash(original, 'dbo.test') != functional_hash(promoted.replace("'test'", "'otro'"), 'dbo.oficial')


def test_unknown_header_stops_instead_of_reconstructing():
    with pytest.raises(RuntimeError):
        split_definition('CREATE VIEW dbo.test AS SELECT 1', 'dbo.test')
