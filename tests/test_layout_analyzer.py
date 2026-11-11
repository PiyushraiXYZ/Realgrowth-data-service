
from app.conversation_analysis.ocr.layout_analyzer import LayoutAnalyzer


def test_layout_analyzer_groups_words_into_lines_and_blocks():
    analyzer = LayoutAnalyzer()

    ocr_result = {
        "words": [
            # First line
            {
                "text": "Hello",
                "confidence": 95,
                "x": 100,
                "y": 100,
                "width": 50,
                "height": 20,
                "line_id": {
                    "page": 1,
                    "block": 1,
                    "paragraph": 1,
                    "line": 1,
                },
            },
            {
                "text": "there",
                "confidence": 90,
                "x": 160,
                "y": 100,
                "width": 45,
                "height": 20,
                "line_id": {
                    "page": 1,
                    "block": 1,
                    "paragraph": 1,
                    "line": 1,
                },
            },

            # Second line, close enough to join the first block
            {
                "text": "How are you?",
                "confidence": 92,
                "x": 100,
                "y": 125,
                "width": 140,
                "height": 20,
                "line_id": {
                    "page": 1,
                    "block": 1,
                    "paragraph": 1,
                    "line": 2,
                },
            },

            # Third line, separated by a large gap
            {
                "text": "Thank you",
                "confidence": 96,
                "x": 100,
                "y": 300,
                "width": 100,
                "height": 20,
                "line_id": {
                    "page": 1,
                    "block": 2,
                    "paragraph": 1,
                    "line": 1,
                },
            },
        ]
    }

    result = analyzer.analyze(
        ocr_result=ocr_result,
        screenshot_index=0,
    )

    assert result["line_count"] == 3
    assert result["block_count"] == 2

    assert result["blocks"][0]["text"] == (
        "Hello there\nHow are you?"
    )

    assert result["blocks"][0]["line_count"] == 2
    assert result["blocks"][0]["word_count"] == 3

    assert result["blocks"][1]["text"] == "Thank you"


def test_layout_analyzer_handles_empty_ocr():
    analyzer = LayoutAnalyzer()

    result = analyzer.analyze({"words": []})

    assert result["line_count"] == 0
    assert result["block_count"] == 0
    assert result["blocks"] == []
