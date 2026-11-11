
from app.conversation_analysis.conversation_reconstructor import (
    conversation_reconstructor,
)


def test_reconstruct_messaging_conversation():
    screenshot_results = [
        {
            "screenshot_index": 1,
            "ocr": {"text": "Rahul: Hello\n10:30 AM"},
            "layout": {
                "blocks": [
                    {"text": "Rahul: Hello", "bbox": {}},
                    {"text": "10:30 AM", "bbox": {}},
                    {"text": "Piyush: Hi Rahul", "bbox": {}},
                ]
            },
        }
    ]

    result = conversation_reconstructor.reconstruct(
        screenshot_results
    )

    assert result["source_type"] == "messaging_or_chat"
    assert result["reconstruction"]["message_count"] == 2
    assert result["messages"][0]["sender"] == "Rahul"


def test_reconstruct_empty_input():
    result = conversation_reconstructor.reconstruct([])

    assert result["source_type"] == "unknown"
    assert result["messages"] == []
    assert result["participants"] == []


if __name__ == "__main__":
    test_reconstruct_messaging_conversation()
    test_reconstruct_empty_input()
    print("Conversation reconstructor tests passed.")
