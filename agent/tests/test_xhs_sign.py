"""签名算法：与文档示例同一拼接规则，向量需以官方为准。"""
from marketing.xiaohongshu.sign import sign_request


def test_sign_request_deterministic():
    s = sign_request(
        "oauth.getAccessToken",
        "app-id-1",
        "1612239430773",
        "2.0",
        "secret-xyz",
    )
    assert len(s) == 32
    assert s == sign_request(
        "oauth.getAccessToken",
        "app-id-1",
        "1612239430773",
        "2.0",
        "secret-xyz",
    )
