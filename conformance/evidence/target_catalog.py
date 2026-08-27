from __future__ import annotations

import ast
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
RUNNER_DIR = ROOT / "conformance" / "runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from _runner_context import build_validator  # noqa: E402


TARGETS_PATH = EVIDENCE_DIR / "targets.json"
TARGET_SCHEMA_PATH = EVIDENCE_DIR / "target_registry.schema.json"
TARGET_CATALOG_PATH = EVIDENCE_DIR / "session_state_projection_v1_target.json"
REPORT_SCHEMA_PATH = EVIDENCE_DIR / "external_evidence_report_v2.schema.json"
REPORT_SCHEMA_V21_PATH = EVIDENCE_DIR / "external_evidence_report_v2_1.schema.json"
REPORT_SCHEMA_V22_PATH = EVIDENCE_DIR / "external_evidence_report_v2_2.schema.json"
TCK_RELEASES_PATH = EVIDENCE_DIR / "evidence_tck_releases.json"
EXPECTATIONS_PATH = EVIDENCE_DIR / "projection_v1_expectations.json"
LEGACY_BUNDLE_MANIFEST_PATH = EVIDENCE_DIR / "evidence_runner_bundle.json"
FROZEN_TCK_1_2_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_2.json"
)
FROZEN_TCK_1_3_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_3.json"
)
FROZEN_TCK_1_4_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_4.json"
)
FROZEN_TCK_1_5_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_5.json"
)
FROZEN_TCK_1_6_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_6.json"
)
FROZEN_TCK_1_7_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_7.json"
)
FROZEN_TCK_1_8_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_8.json"
)
FROZEN_TCK_1_9_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_9.json"
)
FROZEN_TCK_1_10_BUNDLE_MANIFEST_PATH = (
    EVIDENCE_DIR / "evidence_runner_bundle_v1_10.json"
)
BUNDLE_MANIFEST_PATH = EVIDENCE_DIR / "evidence_runner_bundle_v1_11.json"
RELEASE_SNAPSHOT_DIR = EVIDENCE_DIR / "release_registry_snapshots"
PRODUCER_SCENARIO_PATH = EVIDENCE_DIR / "projection_v1_producer_scenario.json"
PRODUCER_TRANSCRIPT_PATH = EVIDENCE_DIR / "projection_v1_producer_transcript.json"
PRODUCER_SCENARIO_SCHEMA_PATH = (
    EVIDENCE_DIR / "projection_v1_producer_scenario.schema.json"
)
TARGET_KEY = "aicp.session_state_projection@v1"
TARGET_ID = "aicp.session_state_projection"
TARGET_VERSION = "v1"
EXPECTED_MARK = "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.1.0"
PROFILE_TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.2.0"
PREVIOUS_TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.3.0"
TCK_1_4_RELEASE_ID = "AICP-EVIDENCE-TCK-1.4.0"
TCK_1_5_RELEASE_ID = "AICP-EVIDENCE-TCK-1.5.0"
TCK_1_6_RELEASE_ID = "AICP-EVIDENCE-TCK-1.6.0"
TCK_1_7_RELEASE_ID = "AICP-EVIDENCE-TCK-1.7.0"
TCK_1_8_RELEASE_ID = "AICP-EVIDENCE-TCK-1.8.0"
TCK_1_9_RELEASE_ID = "AICP-EVIDENCE-TCK-1.9.0"
TCK_1_10_RELEASE_ID = "AICP-EVIDENCE-TCK-1.10.0"
CURRENT_TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.11.0"
HISTORICAL_TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.0.0"
HISTORICAL_RELEASE_RECORD_DIGEST = (
    "sha256:e227fdb2b2d35f83cfeeceff6e80f455ff8a95a1e56244bb6d4433942c53ba80"
)
HISTORICAL_TARGET_SCHEMA_DIGEST = (
    "sha256:a4d63416e0e387ef3e6bff0d3b9397e37a2f380961360a5e4d63096228bcfc50"
)
HISTORICAL_RELEASE_REGISTRY_DIGEST = (
    "sha256:bbc549d1d0ca6344de41a149430c25e257cf3438845f6e4ccdf0eab17f81ceaf"
)
FROZEN_TCK_1_1_RECORD_DIGEST = (
    "sha256:a1b4515821b86a23daff0df9a8b1d6bbf68eec3c5768172c06ed34afb0e7b5cb"
)
FROZEN_TCK_1_2_RECORD_DIGEST = (
    "sha256:71e231798a6e6c9a12e890f64ce0a1d4af26045d426057d5765700af5bb68913"
)
FROZEN_TCK_1_3_RECORD_DIGEST = (
    "sha256:215e87f18e0834d5fd370f8f5d4e298090ed74f67a6e5ed954f5e15204a33fbf"
)
FROZEN_TCK_1_1_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:b480aceb911e7f284352f157f3e04914788bdbdaa95d4c1857ea3ab8ac810426"
)
FROZEN_TCK_1_2_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:2cab009915eb5af6ff1a0940173aaee85fba672b3f2f9bfd578e4c3b1139d60c"
)
FROZEN_TCK_1_3_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:99549237497fe8388a966d338c9d047e414884dc696af872db10032a85efe90b"
)
FROZEN_TCK_1_3_BUNDLE_MANIFEST_DIGEST = (
    "sha256:16ac67d3c290111b206b50313af8e265f6d10a96a55d1b3dc3f5008eef75da53"
)
FROZEN_TCK_1_3_RUNNER_BUNDLE_DIGEST = (
    "sha256:d7d9fc723572d51b65808ccc4eaacc67bb50d2f9e06ac07b0727170bea388d7c"
)
FROZEN_TCK_1_3_REPORT_SCHEMA_DIGEST = (
    "sha256:c4f942cb26818269140faf292c7058f0e9cb4594f0dedecc098ca255888b71cc"
)
FROZEN_TCK_1_3_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:3e71ef6d64826a748cac2ad3de9926232ed5617d5cee88bef43b655f43920d13"
)
FROZEN_TCK_1_3_TARGET_REGISTRY_DIGEST = (
    "sha256:dca00290f63cd360924055293d79f6201d83f128e0fa7db9b737f873cc7a9474"
)
FROZEN_TCK_1_3_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:e90b375a01a7ca469ea1c431f8b763fe74f2ff9934d23c0eff488019ef349ba0",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:aa23e2baf15bbd6b756c6de8317cf1ad7b2d8b5b9567ee759c71e5c5e3ee2076",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:a5d2ddc506878af85f80b71753bb55ffa106302dbf9de4f30b057e1f37a402ed",
}
FROZEN_TCK_1_4_RECORD_DIGEST = (
    "sha256:973dd768f50ed1fa11982feb7bfc14ff8adc98c223dd2a58ec0268f8ab524221"
)
FROZEN_TCK_1_4_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:caae4b440907017075f3829e92c88b718abae600072a83162d55b1991982f2fb"
)
FROZEN_TCK_1_4_BUNDLE_MANIFEST_DIGEST = (
    "sha256:4e7714c5bd82ff7188c68e7d9f7ab38ce58b27f03c4c4f15da394d0ff7a1f004"
)
FROZEN_TCK_1_4_RUNNER_BUNDLE_DIGEST = (
    "sha256:c86e1a86ac5f7125c79132ce2158b47367321079cb85360c26a7574e2b832f4b"
)
FROZEN_TCK_1_4_REPORT_SCHEMA_DIGEST = (
    "sha256:c4f942cb26818269140faf292c7058f0e9cb4594f0dedecc098ca255888b71cc"
)
FROZEN_TCK_1_4_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:3e71ef6d64826a748cac2ad3de9926232ed5617d5cee88bef43b655f43920d13"
)
FROZEN_TCK_1_4_TARGET_REGISTRY_DIGEST = (
    "sha256:ad3164e3c165d3601c30473b6c0185b92f096b822af3bd2325dd48ad0a972a03"
)
FROZEN_TCK_1_4_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:0457228ab0789997d23e6b655fdd3c8447cf5fd7e01d87b7ca34ca120c635948",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:f845e6707f1456b4e8ad0e1ab02b83eacc0647c04053793f1adee973e4fa5a88",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:c1c83123526b3e9e27e8c774086699df968263d1b52360530fabef35923a520d",
}
FROZEN_TCK_1_5_RECORD_DIGEST = (
    "sha256:e1a67c5a3147bf625dbbdd378afc2e3ee62fd52269c38ad382342cea7e687731"
)
FROZEN_TCK_1_5_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:bc669bd4548471042098552693d5f0236354db7c90ba05d56133621edc30f0da"
)
FROZEN_TCK_1_5_BUNDLE_MANIFEST_DIGEST = (
    "sha256:cf38835499b4b33457b73236e00445a6d794d828d5550531644be98262057297"
)
FROZEN_TCK_1_5_RUNNER_BUNDLE_DIGEST = (
    "sha256:6b046eee701611564888585779042d29100bd049c28b5435550c58403a26369d"
)
FROZEN_TCK_1_5_REPORT_SCHEMA_DIGEST = (
    "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
)
FROZEN_TCK_1_5_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:2ce885d972041e631fc67d7a39fa8dbe54d04e123e6277ead6a4accc3b63020f"
)
FROZEN_TCK_1_5_TARGET_REGISTRY_DIGEST = (
    "sha256:64b72ef7cc04a1d555cd8192eb47b67e0d82c392cc72c43a587332e5895b37f5"
)
FROZEN_TCK_1_5_LIVE_TRACE_SCHEMA_DIGEST = (
    "sha256:3e641bfd95ffe6ad0cc3ade7136f10968dc88a62e2519846d55be84730df9fa8"
)
FROZEN_TCK_1_5_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST = (
    "sha256:a7e36ee9b5a8a4de716bcb05b285fb237958566c8dcf8752e8e9b5f586f8c1b5"
)
FROZEN_TCK_1_5_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:0457228ab0789997d23e6b655fdd3c8447cf5fd7e01d87b7ca34ca120c635948",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:f845e6707f1456b4e8ad0e1ab02b83eacc0647c04053793f1adee973e4fa5a88",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:c1c83123526b3e9e27e8c774086699df968263d1b52360530fabef35923a520d",
    "BIND-HTTP@0.1": "sha256:57f08cc8cdba8a36a235e73e07f573556e0fbbcb5dcd7ba35bd4bfbb91f1af2e",
    "BIND-MCP@0.1": "sha256:1dc25ca5709de839d84ea5bc92c1c217d1e2a42d34576902a5c85f808e44bd2f",
}
FROZEN_TCK_1_6_RECORD_DIGEST = (
    "sha256:a2d7e2c7557368573537ddb4dc07aedcadf8c6d7e1cfbdb908d291152d534487"
)
FROZEN_TCK_1_6_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:eda719126cb49eddf48b5b445a80b5e92d6903ec0e8a3b6a6b2f637f31000311"
)
FROZEN_TCK_1_6_BUNDLE_MANIFEST_DIGEST = (
    "sha256:463558c4c83714a80296f855d8ac3cf186fe745d8a9bf1642555ba9a16b605f3"
)
FROZEN_TCK_1_6_RUNNER_BUNDLE_DIGEST = (
    "sha256:853a077c2f4d2cfdf9ac83917c9aa8abee22c48120bc7e7e16fece673f4503ab"
)
FROZEN_TCK_1_6_REPORT_SCHEMA_DIGEST = (
    "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
)
FROZEN_TCK_1_6_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:2ce885d972041e631fc67d7a39fa8dbe54d04e123e6277ead6a4accc3b63020f"
)
FROZEN_TCK_1_6_TARGET_REGISTRY_DIGEST = (
    "sha256:e38a3968683d91519ef4a86815207686d6dac9e5451a893f1c5b57427f48c37c"
)
FROZEN_TCK_1_6_LIVE_TRACE_SCHEMA_DIGEST = (
    "sha256:16722e3a691c9d53989efbe5e45a8c37f82bc6b131dff3f6a517f1f417b49023"
)
FROZEN_TCK_1_6_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST = (
    "sha256:a51f1869d59d6d771e6420bad8b8082606d064af4754c6c25c440ab8c47814d9"
)
FROZEN_TCK_1_6_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:0457228ab0789997d23e6b655fdd3c8447cf5fd7e01d87b7ca34ca120c635948",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:f845e6707f1456b4e8ad0e1ab02b83eacc0647c04053793f1adee973e4fa5a88",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:c1c83123526b3e9e27e8c774086699df968263d1b52360530fabef35923a520d",
    "BIND-HTTP@0.1": "sha256:bd4b101e26264447b5d6d93382acf407d93f04cce2f05a88c601cadca98542bf",
    "BIND-MCP@0.1": "sha256:279b7a3aeac47496c937f5979b9194054605ff054fd68d9696f9089804b21ffe",
}
FROZEN_TCK_1_7_RECORD_DIGEST = (
    "sha256:aee2bc457f7b15054a274d82376c9e15d98106756f1ca4f3ee8401a93d9bc608"
)
FROZEN_TCK_1_7_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:ec3a4470234c37a897c73f6d692e0ede9db44995f1f078ca3e11e93633578d8c"
)
FROZEN_TCK_1_7_BUNDLE_MANIFEST_DIGEST = (
    "sha256:2f64601d851ffc368545633ef29f52f893763ef06fe4e59d4117659b0218f8e6"
)
FROZEN_TCK_1_7_RUNNER_BUNDLE_DIGEST = (
    "sha256:15d3d3506fd6af421cb03fd699f715d32e54226c3ad2709e476cd4d1fa9b917f"
)
FROZEN_TCK_1_7_REPORT_SCHEMA_DIGEST = (
    "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
)
FROZEN_TCK_1_7_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:2ce885d972041e631fc67d7a39fa8dbe54d04e123e6277ead6a4accc3b63020f"
)
FROZEN_TCK_1_7_TARGET_REGISTRY_DIGEST = (
    "sha256:8b0bd1b0bf19e0d3f0c0cf199f6120855360e39eca3169249f4cd6d4de6a6d05"
)
FROZEN_TCK_1_7_LIVE_TRACE_SCHEMA_DIGEST = (
    "sha256:79809571d66260f0dc04a02a2c77c4cbacf88fb1f0f5c1b57d634da90e14a11f"
)
FROZEN_TCK_1_7_PUBLIC_SCENARIO_SCHEMA_DIGEST = (
    "sha256:f4de154a2cba5994981b47dce89a658afb77a777d8c553938323337387b14c71"
)
FROZEN_TCK_1_7_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:0457228ab0789997d23e6b655fdd3c8447cf5fd7e01d87b7ca34ca120c635948",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:f845e6707f1456b4e8ad0e1ab02b83eacc0647c04053793f1adee973e4fa5a88",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:c1c83123526b3e9e27e8c774086699df968263d1b52360530fabef35923a520d",
    "BIND-HTTP@0.1": "sha256:b6e15ef07eac998372408c8da7fb8ee76024ada04f9105f8d91a6dfa647e8fc0",
    "BIND-MCP@0.1": "sha256:035b8711a1d3159be4ecd683d1934c8a2cd3b3487b11712b8428e20d799739d1",
}
FROZEN_TCK_1_8_RECORD_DIGEST = (
    "sha256:ae08dffd8eb85bf5bc7aec8701ed600b16305a24202cf60fbd4d31a1f70b8a56"
)
FROZEN_TCK_1_8_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:cd37d66c92b6f49418b5c9fddb8c30976fce64a0622fd56e6ad16993c26a3f1e"
)
FROZEN_TCK_1_8_BUNDLE_MANIFEST_DIGEST = (
    "sha256:b5d5e9bfece7f0743e336397f45cd9b8a755934468cd854d5f6f3ae1f23c8212"
)
FROZEN_TCK_1_8_RUNNER_BUNDLE_DIGEST = (
    "sha256:8a924f847521ac57c2c57d7d1b1f7b569250a1efbe464dbf92501d42524ca5b5"
)
FROZEN_TCK_1_8_REPORT_SCHEMA_DIGEST = (
    "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
)
FROZEN_TCK_1_8_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:2ce885d972041e631fc67d7a39fa8dbe54d04e123e6277ead6a4accc3b63020f"
)
FROZEN_TCK_1_8_TARGET_REGISTRY_DIGEST = (
    "sha256:180a30bb4218345d59b8d236f9bd20db46ee47253aa78392e17bff767d8f591e"
)
FROZEN_TCK_1_8_LIVE_TRACE_SCHEMA_DIGEST = (
    "sha256:50f2213f90b139a06259d89ef9de40eedba9aee3f3cbb8ed76fbad9bc1fc8030"
)
FROZEN_TCK_1_8_PUBLIC_SCENARIO_SCHEMA_DIGEST = (
    "sha256:f4de154a2cba5994981b47dce89a658afb77a777d8c553938323337387b14c71"
)
FROZEN_TCK_1_8_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:0457228ab0789997d23e6b655fdd3c8447cf5fd7e01d87b7ca34ca120c635948",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:f845e6707f1456b4e8ad0e1ab02b83eacc0647c04053793f1adee973e4fa5a88",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:c1c83123526b3e9e27e8c774086699df968263d1b52360530fabef35923a520d",
    "BIND-HTTP@0.1": "sha256:00d440218fb22148ba277b3ebc67beff610cb0dec7bd927409dcd03b0e9cdba3",
    "BIND-MCP@0.1": "sha256:1fa9fd9b3c30758e9561f771c30aba5be608ac2bfe07629fd36297430b67d651",
}
FROZEN_TCK_1_9_RECORD_DIGEST = (
    "sha256:5169403b16a0545b01416782a589ff9c9c2c49cf84fc980b9ce1493637f66952"
)
FROZEN_TCK_1_9_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:6a5151d9997e121fe911600f98e8b8eef599b78d7ad8ff15ffffdf71cc9fd4b6"
)
FROZEN_TCK_1_9_BUNDLE_MANIFEST_DIGEST = (
    "sha256:02fc976c5d03b8bce433f4bdfdff4d3429bbe7b0c30c58fb782218aa71c7ce92"
)
FROZEN_TCK_1_9_RUNNER_BUNDLE_DIGEST = (
    "sha256:d6436082395af5ceca8aad609512d89f869e9b6db8e1f6c31c0a4deae56648db"
)
FROZEN_TCK_1_9_REPORT_SCHEMA_DIGEST = (
    "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
)
FROZEN_TCK_1_9_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:2ce885d972041e631fc67d7a39fa8dbe54d04e123e6277ead6a4accc3b63020f"
)
FROZEN_TCK_1_9_TARGET_REGISTRY_DIGEST = (
    "sha256:775ff6d7d9c247d151180efbb1143fe45ece0906ad77e493390e1a5b3a1e9818"
)
FROZEN_TCK_1_9_LIVE_TRACE_SCHEMA_DIGEST = (
    "sha256:50f2213f90b139a06259d89ef9de40eedba9aee3f3cbb8ed76fbad9bc1fc8030"
)
FROZEN_TCK_1_9_PUBLIC_SCENARIO_SCHEMA_DIGEST = (
    "sha256:f4de154a2cba5994981b47dce89a658afb77a777d8c553938323337387b14c71"
)
FROZEN_TCK_1_9_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:8fb426b9952294815fc5d41477b9338ad95bb29670ba04a0536d445c8bfadf7c",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:1565182e521f747044019b09b45320f74ffa6245521f8ddaec98340473fc725b",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:feb39f645b84ab6eb07164d5c5e5d548b2f121347b478fa6fa9407645c4523dc",
    "BIND-HTTP@0.1": "sha256:00d440218fb22148ba277b3ebc67beff610cb0dec7bd927409dcd03b0e9cdba3",
    "BIND-MCP@0.1": "sha256:1fa9fd9b3c30758e9561f771c30aba5be608ac2bfe07629fd36297430b67d651",
}
FROZEN_TCK_1_10_RECORD_DIGEST = (
    "sha256:caed5afec58101d1e108f5e64a31f953dca492d8d4a079b173f54591af33eeaf"
)
FROZEN_TCK_1_10_REGISTRY_SNAPSHOT_DIGEST = (
    "sha256:7f57814d35cab7d7d50241b41ede7eb182e2b9f890928d04a6c872bb19f743dc"
)
FROZEN_TCK_1_10_BUNDLE_MANIFEST_DIGEST = (
    "sha256:c61e9f4a1e384bcd435765d1457223b2cae1035c62686fedaa7101681d19919b"
)
FROZEN_TCK_1_10_RUNNER_BUNDLE_DIGEST = (
    "sha256:77498e0b1801a2fdc94ebc7947fe3f9df5395332ef272f49ce7cecb6050ceed0"
)
FROZEN_TCK_1_10_REPORT_SCHEMA_DIGEST = (
    "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
)
FROZEN_TCK_1_10_TARGET_REGISTRY_SCHEMA_DIGEST = (
    "sha256:2ce885d972041e631fc67d7a39fa8dbe54d04e123e6277ead6a4accc3b63020f"
)
FROZEN_TCK_1_10_TARGET_REGISTRY_DIGEST = (
    "sha256:6aaa954733282583cd32311956af00ef6599f984af99e09f7d330c479f50924b"
)
FROZEN_TCK_1_10_LIVE_TRACE_SCHEMA_DIGEST = (
    "sha256:50f2213f90b139a06259d89ef9de40eedba9aee3f3cbb8ed76fbad9bc1fc8030"
)
FROZEN_TCK_1_10_PUBLIC_SCENARIO_SCHEMA_DIGEST = (
    "sha256:f4de154a2cba5994981b47dce89a658afb77a777d8c553938323337387b14c71"
)
FROZEN_TCK_1_10_TARGET_CATALOG_DIGESTS = {
    TARGET_KEY: "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
    "AICP-MEDIATED-BLOCKING@0.1": "sha256:b05ee4fdc5779e7c41710d7cee4c8912e6dbe03cd57c270027f7ddb8c6ef007c",
    "AICP-RESUMABLE-SESSIONS@0.1": "sha256:a433771d9f56ed915d95e36e7f92f121e9d19c31817dd6f131194f725114fe36",
    "AICP-DELEGATED-IDENTITY@0.1": "sha256:67876256e416ed4edfb4ceff16e736d28b6fba94fb00dda8fc5c69dd188de1c8",
    "BIND-HTTP@0.1": "sha256:00d440218fb22148ba277b3ebc67beff610cb0dec7bd927409dcd03b0e9cdba3",
    "BIND-MCP@0.1": "sha256:1fa9fd9b3c30758e9561f771c30aba5be608ac2bfe07629fd36297430b67d651",
}
PROFILE_TARGET_KEYS = (
    "AICP-MEDIATED-BLOCKING@0.1",
    "AICP-RESUMABLE-SESSIONS@0.1",
    "AICP-DELEGATED-IDENTITY@0.1",
)
BINDING_TARGET_KEYS = ("BIND-HTTP@0.1", "BIND-MCP@0.1")
EXPECTED_TARGET_KEYS = (TARGET_KEY, *PROFILE_TARGET_KEYS, *BINDING_TARGET_KEYS)
TARGET_KINDS = {"product_profile", "capability", "binding"}
TARGET_KIND_POLICY = {
    "product_profile": ("full-profile", "implements_profile"),
    "capability": ("full-capability", "implements_capability"),
    "binding": ("full-binding", "implements_binding"),
}


@dataclass(frozen=True)
class TargetRecord:
    target_key: str
    target_kind: str
    target_id: str
    target_version: str
    status: str
    catalog_path: str
    expected_mark: str
    execution_mode: str
    evidence_claim_type: str
    handler_id: str
    current_release_id: str
    required_suites: tuple[str, ...]
    required_operations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, item: dict[str, Any]) -> "TargetRecord":
        return cls(
            target_key=str(item["target_key"]),
            target_kind=str(item["target_kind"]),
            target_id=str(item["target_id"]),
            target_version=str(item["target_version"]),
            status=str(item["status"]),
            catalog_path=str(item["catalog_path"]),
            expected_mark=str(item["expected_mark"]),
            execution_mode=str(item["execution_mode"]),
            evidence_claim_type=str(item["evidence_claim_type"]),
            handler_id=str(item["handler_id"]),
            current_release_id=str(item["current_release_id"]),
            required_suites=tuple(str(value) for value in item["required_suites"]),
            required_operations=tuple(
                str(value) for value in item["required_operations"]
            ),
        )

    def identity(self) -> dict[str, str]:
        return {
            "kind": self.target_kind,
            "target_id": self.target_id,
            "target_version": self.target_version,
        }


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(
        data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    ).hexdigest()


def file_digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical_digest(value: Any) -> str:
    data = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return digest_bytes(data)


def canonical_target_key(kind: str, target_id: str, version: str) -> str:
    if kind not in TARGET_KINDS:
        raise ValueError(f"unknown evidence target kind: {kind}")
    for label, value in (("target_id", target_id), ("target_version", version)):
        if (
            not isinstance(value, str)
            or not value
            or "@" in value
            or any(character.isspace() for character in value)
        ):
            raise ValueError(f"{label} must be a non-empty unambiguous exact value")
    return f"{target_id}@{version}"


def target_registry() -> dict[str, Any]:
    value = load_json(TARGETS_PATH)
    if not isinstance(value, dict):
        raise ValueError("evidence target registry must be an object")
    return value


def release_registry() -> dict[str, Any]:
    value = load_json(TCK_RELEASES_PATH)
    if not isinstance(value, dict):
        raise ValueError("evidence TCK release registry must be an object")
    return value


def release_snapshot_path(release_id: str) -> Path:
    if not isinstance(release_id, str) or not release_id.startswith("AICP-EVIDENCE-TCK-"):
        raise ValueError("invalid evidence TCK release snapshot identity")
    return RELEASE_SNAPSHOT_DIR / f"{release_id}.json"


def release_snapshot(release_id: str) -> dict[str, Any]:
    path = release_snapshot_path(release_id)
    if not path.is_file():
        raise ValueError(f"evidence TCK release snapshot is missing: {release_id}")
    value = load_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"evidence TCK release snapshot must be an object: {release_id}")
    release_record(release_id, value)
    return value


def release_snapshot_digest(release_id: str) -> str:
    path = release_snapshot_path(release_id)
    if not path.is_file():
        raise ValueError(f"evidence TCK release snapshot is missing: {release_id}")
    return file_digest(path)


def release_policy(
    release_id: str,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = registry if registry is not None else release_registry()
    matches = [
        item
        for item in value.get("release_policies", [])
        if isinstance(item, dict) and item.get("release_id") == release_id
    ]
    if len(matches) != 1:
        raise ValueError(f"evidence TCK release policy must resolve exactly once: {release_id}")
    return matches[0]


def resolve_target_record(
    target_key: str,
    registry: dict[str, Any] | None = None,
) -> TargetRecord:
    value = registry if registry is not None else target_registry()
    matches = [
        item
        for item in value.get("targets", [])
        if isinstance(item, dict) and item.get("target_key") == target_key
    ]
    if len(matches) != 1:
        raise ValueError(f"target must resolve exactly once: {target_key}")
    record = TargetRecord.from_mapping(matches[0])
    if record.target_key != canonical_target_key(
        record.target_kind,
        record.target_id,
        record.target_version,
    ):
        raise ValueError("target key is ambiguous or does not match exact identity")
    return record


def target_record(target_key: str = TARGET_KEY) -> TargetRecord:
    return resolve_target_record(target_key)


def target_catalog(record: TargetRecord | None = None) -> dict[str, Any]:
    selected = record or target_record()
    value = load_json(ROOT / selected.catalog_path)
    if not isinstance(value, dict):
        raise ValueError("evidence target catalog must be an object")
    return value


def release_record(
    release_id: str = TCK_RELEASE_ID,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = registry if registry is not None else release_registry()
    matches = [
        item
        for item in value.get("releases", [])
        if isinstance(item, dict) and item.get("release_id") == release_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"evidence TCK release must resolve exactly once: {release_id}"
        )
    return matches[0]


def release_supersession(
    release_id: str,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    value = registry if registry is not None else release_registry()
    for item in value.get("supersessions", []):
        if isinstance(item, dict) and item.get("release_id") == release_id:
            return item
    return None


def release_target_entry(
    release: dict[str, Any],
    target_key: str | None = None,
) -> dict[str, Any]:
    singular = release.get("target")
    if isinstance(singular, dict):
        if target_key is not None and singular.get("target_key") != target_key:
            raise ValueError("declared release does not contain the exact target")
        return singular
    targets = release.get("targets")
    if not isinstance(targets, list) or not isinstance(target_key, str):
        raise ValueError("multi-target evidence release requires an exact target key")
    matches = [
        item
        for item in targets
        if isinstance(item, dict) and item.get("target_key") == target_key
    ]
    if len(matches) != 1:
        raise ValueError("declared release must contain the exact target once")
    return matches[0]


def expected_input_artifacts(
    release: dict[str, Any],
    target_key: str | None = None,
) -> list[dict[str, str]]:
    try:
        target = release_target_entry(release, target_key)
    except ValueError:
        return []
    return [
        {
            "path": str(item["path"]),
            "content_digest": str(item["content_digest"]),
        }
        for item in target.get("required_input_artifacts", []) or []
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and isinstance(item.get("content_digest"), str)
    ]


def expected_suite_records(
    release: dict[str, Any],
    target_key: str | None = None,
) -> list[dict[str, str]]:
    try:
        target = release_target_entry(release, target_key)
    except ValueError:
        return []
    return [
        {
            "suite_id": str(item["suite_id"]),
            "suite_version": str(item["suite_version"]),
            "path": str(item["path"]),
            "suite_digest": str(item["suite_digest"]),
        }
        for item in target.get("required_suites", []) or []
        if isinstance(item, dict)
    ]


def mandatory_case_ids(
    catalog: dict[str, Any],
    mode: str,
    handler: Any,
) -> list[str]:
    if hasattr(handler, "mandatory_case_ids"):
        return list(handler.mandatory_case_ids(catalog, mode))
    ids = [
        "EVIDENCE-TARGET-CATALOG-01",
        "EVIDENCE-TCK-PROVENANCE-01",
        "EVIDENCE-RUNNER-WORKTREE-01",
        "EVIDENCE-DESCRIBE-START-01",
    ]
    ids.extend(
        str(item["case_id"])
        for item in catalog.get("canonicalization_vectors", [])
    )
    producer_records = (
        handler.producer_cases(catalog, mode)
        if hasattr(handler, "producer_cases")
        else [catalog["producer_case"]]
    )
    ids.extend(str(item["case_id"]) for item in producer_records)
    ids.extend(
        str(item["case_id"])
        for item in handler.consumer_cases(catalog, mode)
    )
    ids.extend(
        ["EVIDENCE-DESCRIBE-STABILITY-01", "EVIDENCE-TARGET-SUPPORT-01"]
    )
    return ids


def _registered_reference_valid(
    record: TargetRecord,
    *,
    root: Path,
) -> bool:
    if record.target_kind == "capability":
        return (
            record.target_id == TARGET_ID
            and record.target_version == TARGET_VERSION
        )
    if record.target_kind == "product_profile":
        profiles = load_json(root / "registry/aicp_profiles.json")
        return any(
            isinstance(item, dict)
            and item.get("profile_id") == record.target_id
            and item.get("profile_version") == record.target_version
            for item in profiles
        )
    bindings = load_json(root / "registry/transport_bindings.json")
    canonical_id = f"{record.target_id}-{record.target_version}"
    return any(
        isinstance(item, dict)
        and item.get("id") == canonical_id
        and item.get("status") != "deprecated"
        for item in bindings
    )


def validate_target_registry(
    registry: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    simulate_no_jsonschema: bool = False,
    require_repository_references: bool = True,
    enforce_current_scope: bool | None = None,
) -> list[str]:
    value = registry if registry is not None else target_registry()
    errors: list[str] = []
    if enforce_current_scope is None:
        enforce_current_scope = registry is None
    schema_path = root / "conformance/evidence/target_registry.schema.json"
    schema = load_json(schema_path)
    validator = None if simulate_no_jsonschema else build_validator(schema, schema_path)
    if validator is None:
        errors.append(
            "jsonschema is required to validate the evidence target registry"
        )
    else:
        for issue in sorted(
            validator.iter_errors(value),
            key=lambda item: list(item.path),
        ):
            pointer = "/" + "/".join(str(part) for part in issue.path)
            errors.append(f"target registry schema error at {pointer}: {issue.message}")

    targets = value.get("targets") if isinstance(value, dict) else None
    if not isinstance(targets, list) or not targets:
        return sorted(set([*errors, "target registry must contain targets"]))
    keys: list[str] = []
    marks: list[str] = []
    identities: list[tuple[str, str, str]] = []
    identities_by_key: dict[str, set[tuple[str, str, str]]] = {}
    profile_registry = load_json(root / "registry/aicp_profiles.json")
    profile_entries = {
        (str(item.get("profile_id")), str(item.get("profile_version"))): item
        for item in profile_registry
        if isinstance(item, dict)
    }
    releases_value = (
        release_registry()
        if require_repository_references and root == ROOT
        else load_json(root / "conformance/evidence/evidence_tck_releases.json")
        if require_repository_references
        and (root / "conformance/evidence/evidence_tck_releases.json").is_file()
        else None
    )
    for item in targets:
        if not isinstance(item, dict):
            errors.append("target records must be objects")
            continue
        try:
            record = TargetRecord.from_mapping(item)
            expected_key = canonical_target_key(
                record.target_kind,
                record.target_id,
                record.target_version,
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"invalid target record: {exc}")
            continue
        keys.append(record.target_key)
        marks.append(record.expected_mark)
        identity = (
            record.target_kind,
            record.target_id,
            record.target_version,
        )
        identities.append(identity)
        identities_by_key.setdefault(record.target_key, set()).add(identity)
        if record.target_key != expected_key:
            errors.append(
                f"target key does not exactly match identity: {record.target_key}"
            )
        if require_repository_references and not _registered_reference_valid(
            record,
            root=root,
        ):
            errors.append(
                f"target identity is not registered: {record.target_key}"
            )
        expected_mode, expected_claim = TARGET_KIND_POLICY[record.target_kind]
        if record.execution_mode != expected_mode:
            errors.append(
                f"target kind/execution mode mismatch: {record.target_key}"
            )
        if record.evidence_claim_type != expected_claim:
            errors.append(
                f"target kind/claim type mismatch: {record.target_key}"
            )
        catalog_path = root / record.catalog_path
        if require_repository_references:
            for relative in (record.catalog_path, *record.required_suites):
                if not (root / relative).is_file():
                    errors.append(f"target registry path does not resolve: {relative}")
            if catalog_path.is_file():
                catalog_value = load_json(catalog_path)
                if catalog_value.get("target") != record.identity():
                    errors.append(
                        f"target catalog identity mismatch: {record.target_key}"
                    )
                if catalog_value.get("handler_id") != record.handler_id:
                    errors.append(
                        f"target registry handler mismatch: {record.target_key}"
                    )
                if catalog_value.get("expected_mark") != record.expected_mark:
                    errors.append(
                        f"target registry mark mismatch: {record.target_key}"
                    )
                if tuple(catalog_value.get("required_suite_paths", record.required_suites)) != record.required_suites:
                    errors.append(
                        f"target registry required suites mismatch: {record.target_key}"
                    )
                if tuple(catalog_value.get("required_operations", ())) != record.required_operations:
                    errors.append(
                        f"target registry required operations mismatch: {record.target_key}"
                    )
            if record.target_kind == "product_profile":
                profile = profile_entries.get((record.target_id, record.target_version))
                if not isinstance(profile, dict) or profile.get("status") != record.status:
                    errors.append(
                        f"target maturity differs from profile registry: {record.target_key}"
                    )
                if catalog_path.is_file():
                    catalog_value = load_json(catalog_path)
                    profile_path_value = catalog_value.get("profile_catalog", {}).get("path")
                    if not isinstance(profile_path_value, str) or not (root / profile_path_value).is_file():
                        errors.append(
                            f"profile target catalog does not bind a profile catalog: {record.target_key}"
                        )
                    else:
                        profile_catalog = load_json(root / profile_path_value)
                        if profile_catalog.get("compatibility_mark") != record.expected_mark:
                            errors.append(
                                f"profile mark differs from owning catalog: {record.target_key}"
                            )
                        if tuple(profile_catalog.get("required_suites", ())) != record.required_suites:
                            errors.append(
                                f"profile suites differ from owning catalog: {record.target_key}"
                            )
        if releases_value is not None:
            try:
                selected_release = release_record(record.current_release_id, releases_value)
                release_target = release_target_entry(selected_release, record.target_key)
            except ValueError as exc:
                errors.append(f"target current release is invalid: {record.target_key}: {exc}")
            else:
                if release_target.get("handler_id") != record.handler_id:
                    errors.append(f"release handler mismatch: {record.target_key}")
                if release_target.get("expected_mark") != record.expected_mark:
                    errors.append(f"release mark mismatch: {record.target_key}")
    if len(keys) != len(set(keys)):
        errors.append("target keys must be unique")
    if len(marks) != len(set(marks)):
        errors.append("target expected marks must be unique")
    if len(identities) != len(set(identities)):
        errors.append("exact target identities must be unique")
    if any(len(values) != 1 for values in identities_by_key.values()):
        errors.append("the same target key maps to different identities")
    if enforce_current_scope and keys != list(EXPECTED_TARGET_KEYS):
        errors.append(
            "M64 must register projection v1, the three Tier-1 profiles, and two live binding targets"
        )
    return sorted(set(errors))


def validate_target_catalog(
    catalog: dict[str, Any] | None = None,
    *,
    record: TargetRecord | None = None,
    handler: Any | None = None,
    root: Path = ROOT,
    simulate_no_jsonschema: bool = False,
) -> list[str]:
    selected = record or target_record()
    value = catalog if catalog is not None else target_catalog(selected)
    if selected.target_kind == "product_profile":
        return _validate_product_profile_catalog(
            value,
            selected=selected,
            handler=handler,
            root=root,
            simulate_no_jsonschema=simulate_no_jsonschema,
        )
    if selected.target_kind == "binding":
        errors: list[str] = []
        if value.get("target") != selected.identity():
            errors.append("binding target catalog identity differs from target registry")
        if value.get("target_key") != selected.target_key:
            errors.append("binding target catalog key differs from target registry")
        if value.get("handler_id") != selected.handler_id:
            errors.append("binding target handler differs from target registry")
        if value.get("expected_mark") != selected.expected_mark:
            errors.append("binding target mark differs from target registry")
        if tuple(value.get("required_operations", ())) != selected.required_operations:
            errors.append("binding target operation set differs from target registry")
        suites = value.get("required_suites")
        if not isinstance(suites, list):
            errors.append("binding target required_suites must be an array")
        else:
            if [item.get("path") for item in suites if isinstance(item, dict)] != list(selected.required_suites):
                errors.append("binding target suite records differ from registry")
            for item in suites:
                if not isinstance(item, dict):
                    errors.append("binding target suite record is not an object")
                    continue
                relative = item.get("path")
                if not isinstance(relative, str) or not (root / relative).is_file():
                    errors.append(f"binding target suite does not resolve: {relative}")
                    continue
                suite = load_json(root / relative)
                if item.get("suite_id") != suite.get("suite_id") or item.get("suite_version") != suite.get("suite_version"):
                    errors.append(f"binding target suite identity is stale: {relative}")
                if item.get("suite_digest") != file_digest(root / relative):
                    errors.append(f"binding target suite digest is stale: {relative}")
        if handler is not None:
            ids = mandatory_case_ids(value, selected.execution_mode, handler)
            if len(ids) != len(set(ids)):
                errors.append("binding target mandatory evidence case IDs are not unique")
            errors.extend(
                handler.validate_catalog(
                    value,
                    simulate_no_jsonschema=simulate_no_jsonschema,
                )
            )
        return sorted(set(errors))
    errors: list[str] = []
    suite_ref = value.get("owning_suite", {}).get("path")
    if not isinstance(suite_ref, str) or not (root / suite_ref).is_file():
        return ["target catalog owning suite does not resolve"]
    suite = load_json(root / suite_ref)
    source_cases = {
        str(item["id"]): item
        for item in suite.get("transcripts", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    consumers = value.get("consumer_cases")
    if not isinstance(consumers, list):
        return ["target catalog consumer_cases must be an array"]
    observed = [
        str(item.get("source_case_id"))
        for item in consumers
        if isinstance(item, dict)
    ]
    if Counter(observed) != Counter(source_cases.keys()):
        errors.append(
            "target catalog must cover every owning-suite transcript exactly once"
        )
    if value.get("consumer_error_ordering") != (
        "observation-list order, repeated code exact_count times"
    ):
        errors.append("consumer error ordering semantics are not explicit")
    for item in consumers:
        if not isinstance(item, dict):
            errors.append("consumer case records must be objects")
            continue
        source_id = str(item.get("source_case_id"))
        source = source_cases.get(source_id)
        if source is None:
            errors.append(f"unknown source transcript: {source_id}")
            continue
        expected_accepted = source.get("expect_pass", True) is True
        if item.get("accepted") is not expected_accepted:
            errors.append(f"consumer acceptance drifts from owning suite: {source_id}")
        suite_codes = Counter(
            str(failure.get("test_id"))
            for failure in source.get("expected_failures", [])
            if isinstance(failure, dict)
        )
        observations = item.get("expected_error_observations")
        if not isinstance(observations, list):
            errors.append(f"consumer observations are missing: {source_id}")
            continue
        reviewed_counts: Counter[str] = Counter()
        for observation in observations:
            if not isinstance(observation, dict):
                errors.append(f"consumer observation must be an object: {source_id}")
                continue
            code = observation.get("code")
            count = observation.get("exact_count")
            scope = observation.get("check_scope")
            if not isinstance(code, str) or not code:
                errors.append(f"consumer observation code is invalid: {source_id}")
                continue
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                errors.append(f"consumer observation count is invalid: {source_id}")
                continue
            if not isinstance(scope, str) or not scope:
                errors.append(f"consumer observation scope is missing: {source_id}")
            reviewed_counts[code] += count
            if count > suite_codes[code] and not observation.get(
                "supplemental_reason"
            ):
                errors.append(
                    f"supplemental consumer observation lacks rationale: {source_id}/{code}"
                )
        if any(reviewed_counts[code] < count for code, count in suite_codes.items()):
            errors.append(
                f"consumer observations omit owning-suite expectation: {source_id}"
            )
        fixture = item.get("fixture")
        if fixture != source.get("path"):
            errors.append(f"consumer fixture drifts from owning suite: {source_id}")
    producer = value.get("producer_case")
    if not isinstance(producer, dict):
        errors.append("target catalog producer case is missing")
    ids = (
        mandatory_case_ids(value, "full-capability", handler)
        if handler is not None
        else []
    )
    if ids and len(ids) != len(set(ids)):
        errors.append("mandatory evidence case IDs must be unique")
    for artifact in value.get("required_input_artifacts", []):
        if not isinstance(artifact, dict):
            errors.append("required input artifact records must be objects")
            continue
        relative = artifact.get("path")
        if not isinstance(relative, str) or not (root / relative).is_file():
            errors.append(f"required input artifact does not resolve: {relative}")
            continue
        if artifact.get("content_digest") != file_digest(root / relative):
            errors.append(f"required input digest is stale: {relative}")
    owning = value.get("owning_suite", {})
    if owning.get("suite_digest") != file_digest(root / suite_ref):
        errors.append("owning suite digest is stale")
    if value.get("target") != selected.identity():
        errors.append("target catalog identity does not match the registry record")
    if value.get("target_key") != selected.target_key:
        errors.append("target catalog key does not match the registry record")
    if value.get("expected_mark") != selected.expected_mark:
        errors.append("target catalog mark does not match the registry record")
    if handler is not None:
        errors.extend(
            handler.validate_catalog(
                value,
                simulate_no_jsonschema=simulate_no_jsonschema,
            )
        )
    return sorted(set(errors))


def _validate_product_profile_catalog(
    value: dict[str, Any],
    *,
    selected: TargetRecord,
    handler: Any | None,
    root: Path,
    simulate_no_jsonschema: bool,
) -> list[str]:
    errors: list[str] = []
    profile_record = value.get("profile_catalog")
    if not isinstance(profile_record, dict):
        return ["profile evidence target catalog lacks profile_catalog provenance"]
    profile_path = profile_record.get("path")
    if not isinstance(profile_path, str) or not (root / profile_path).is_file():
        return ["profile evidence target owning profile catalog does not resolve"]
    profile = load_json(root / profile_path)
    if (
        profile.get("profile_id") != selected.target_id
        or profile.get("profile_version") != selected.target_version
    ):
        errors.append("profile target catalog identity differs from owning profile")
    if profile.get("compatibility_mark") != selected.expected_mark:
        errors.append("profile target catalog mark differs from owning profile")
    required_suite_paths = list(profile.get("required_suites", []))
    if value.get("required_suite_paths") != required_suite_paths:
        errors.append("profile target required suites differ from owning profile")
    if profile_record.get("content_digest") != file_digest(root / profile_path):
        errors.append("profile catalog digest is stale")

    suite_records = value.get("required_suites")
    if not isinstance(suite_records, list):
        return sorted(set([*errors, "profile target required_suites must be an array"]))
    if [item.get("path") for item in suite_records if isinstance(item, dict)] != required_suite_paths:
        errors.append("profile target suite records are missing, duplicated, or reordered")
    expected_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for suite_record in suite_records:
        if not isinstance(suite_record, dict):
            errors.append("profile target suite record must be an object")
            continue
        relative = suite_record.get("path")
        if not isinstance(relative, str) or not (root / relative).is_file():
            errors.append(f"profile target suite does not resolve: {relative}")
            continue
        suite = load_json(root / relative)
        if suite_record.get("suite_id") != suite.get("suite_id") or suite_record.get(
            "suite_version"
        ) != suite.get("suite_version"):
            errors.append(f"profile target suite identity is stale: {relative}")
        if suite_record.get("suite_digest") != file_digest(root / relative):
            errors.append(f"profile target suite digest is stale: {relative}")
        for transcript in suite.get("transcripts", []):
            if isinstance(transcript, dict) and isinstance(transcript.get("id"), str):
                expected_sources[(str(suite.get("suite_id")), str(transcript["id"]))] = {
                    "suite_path": relative,
                    "transcript": transcript,
                }

    consumers = value.get("consumer_cases")
    if not isinstance(consumers, list):
        return sorted(set([*errors, "profile target consumer_cases must be an array"]))
    observed_sources = Counter(
        (str(item.get("source_suite_id")), str(item.get("source_case_id")))
        for item in consumers
        if isinstance(item, dict)
    )
    if observed_sources != Counter({key: 1 for key in expected_sources}):
        errors.append("profile target must cover every required-suite transcript exactly once")
    case_ids = [item.get("case_id") for item in consumers if isinstance(item, dict)]
    if len(case_ids) != len(set(case_ids)):
        errors.append("profile target public consumer case IDs must be globally unique")
    for item in consumers:
        if not isinstance(item, dict):
            errors.append("profile target consumer case must be an object")
            continue
        source_key = (str(item.get("source_suite_id")), str(item.get("source_case_id")))
        source = expected_sources.get(source_key)
        if source is None:
            errors.append(f"profile target consumer source is unknown: {source_key}")
            continue
        transcript = source["transcript"]
        fixture = transcript.get("path")
        if item.get("fixture") != fixture:
            errors.append(f"profile target consumer fixture drift: {source_key}")
        if isinstance(fixture, str) and item.get("input_digest") != file_digest(root / fixture):
            errors.append(f"profile target consumer fixture digest is stale: {source_key}")
        expected_accepted = transcript.get("expect_pass", True) is True
        if item.get("accepted") is not expected_accepted:
            errors.append(f"profile target consumer acceptance drift: {source_key}")
        suite_codes = [
            str(failure.get("test_id"))
            for failure in transcript.get("expected_failures", [])
            if isinstance(failure, dict) and isinstance(failure.get("test_id"), str)
        ]
        observations = item.get("expected_error_observations")
        if not isinstance(observations, list):
            errors.append(f"profile target reviewed observation missing: {source_key}")
            continue
        reviewed_codes: list[str] = []
        for observation in observations:
            if not isinstance(observation, dict):
                errors.append(f"profile target observation is not an object: {source_key}")
                continue
            code = observation.get("code")
            count = observation.get("exact_count")
            scope = observation.get("check_scope")
            if not isinstance(code, str) or not isinstance(count, int) or count < 1:
                errors.append(f"profile target observation is invalid: {source_key}")
                continue
            if not isinstance(scope, str) or not scope:
                errors.append(f"profile target observation scope missing: {source_key}")
            reviewed_codes.extend([code] * count)
            if code not in suite_codes and not observation.get("supplemental_reason"):
                errors.append(f"profile target supplemental observation lacks rationale: {source_key}/{code}")
        if reviewed_codes != suite_codes:
            errors.append(f"profile target observations differ from reviewed suite order: {source_key}")

    if value.get("target") != selected.identity() or value.get("target_key") != selected.target_key:
        errors.append("profile target catalog identity differs from target registry")
    if value.get("handler_id") != selected.handler_id:
        errors.append("profile target catalog handler differs from target registry")
    if value.get("expected_mark") != selected.expected_mark:
        errors.append("profile target catalog mark differs from target registry")
    if tuple(value.get("required_operations", ())) != selected.required_operations:
        errors.append("profile target operation set differs from target registry")
    for artifact in value.get("required_input_artifacts", []):
        if not isinstance(artifact, dict):
            errors.append("profile target required input record must be an object")
            continue
        relative = artifact.get("path")
        if not isinstance(relative, str) or not (root / relative).is_file():
            errors.append(f"profile target required input does not resolve: {relative}")
        elif artifact.get("content_digest") != file_digest(root / relative):
            errors.append(f"profile target required input digest is stale: {relative}")
    if handler is not None:
        try:
            ids = mandatory_case_ids(value, "full-profile", handler)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"profile target mandatory case derivation failed: {exc}")
        else:
            if len(ids) != len(set(ids)):
                errors.append("profile target mandatory evidence case IDs are not unique")
        errors.extend(
            handler.validate_catalog(
                value,
                simulate_no_jsonschema=simulate_no_jsonschema,
            )
        )
    return sorted(set(errors))


_BUNDLE_SEEDS = (
    "conformance/evidence/aicp_external_evidence_runner.py",
    "conformance/evidence/aicp_live_binding_runner.py",
    "conformance/evidence/report_evaluator.py",
    "conformance/evidence/target_catalog.py",
    "conformance/evidence/target_handlers.py",
)
_BUNDLE_ROLES = {
    "conformance/evidence/aicp_external_evidence_runner.py": "runner",
    "conformance/evidence/aicp_live_binding_runner.py": "live_binding_runner",
    "conformance/evidence/report_evaluator.py": "evaluator",
    "conformance/evidence/target_catalog.py": "target_dispatch",
    "conformance/evidence/target_handlers.py": "target_dispatch",
    "conformance/evidence/projection_v1_handler.py": "target_handler",
    "conformance/evidence/product_profile_handler.py": "target_handler",
    "conformance/evidence/live_bindings/__init__.py": "package_initialization",
    "conformance/evidence/live_bindings/live_binding_handler.py": "target_handler",
    "conformance/evidence/live_bindings/live_binding_trace.py": "live_trace_evaluation",
    "conformance/evidence/live_bindings/live_binding_process.py": "process_supervision",
    "conformance/evidence/live_bindings/live_http_capture.py": "transport_capture",
    "conformance/evidence/live_bindings/live_http_transport.py": "live_http_transport",
    "conformance/evidence/live_bindings/live_mcp_capture.py": "transport_capture",
    "conformance/evidence/live_bindings/live_mcp_transport.py": "live_mcp_transport",
    "conformance/evidence/live_bindings/live_tls.py": "tls_runtime",
    "conformance/evidence/live_bindings/live_trace_evaluator.py": "live_trace_evaluation",
    "conformance/evidence/live_bindings/live_trace_normalization.py": "semantic_normalization",
    "conformance/evidence/profile_transcript_evaluator.py": "transcript_validation",
    "conformance/evidence/producer_payload_schema_router.py": "payload_schema_routing",
    "conformance/evidence/producer_suite_semantics.py": "producer_semantic_dispatch",
    "conformance/evidence/adapter_process.py": "process_supervision",
    "conformance/evidence/evidence_identifier_rules.py": "identifier_semantics",
    "conformance/runner/_runner_context.py": "report_schema_support",
    "reference/python/aicp_ref/hashing.py": "canonicalization",
    "reference/python/aicp_ref/jcs.py": "canonicalization",
    "reference/python/aicp_ref/signatures.py": "dependency_probe",
    "reference/python/aicp_ref/__init__.py": "package_initialization",
}


def _local_module_map(root: Path) -> dict[str, str]:
    modules: dict[str, str] = {}
    roots = (
        root / "conformance/evidence",
        root / "conformance/runner",
        root / "conformance/iut",
        root / "reference/python",
    )
    for base in roots:
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            relative = path.relative_to(root).as_posix()
            parts = list(path.relative_to(base).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts = parts[:-1]
            module = ".".join(parts)
            if module:
                modules.setdefault(module, relative)
    return modules


def _module_for_path(path: str) -> str:
    relative = Path(path)
    for prefix in (
        "conformance/evidence",
        "conformance/runner",
        "conformance/iut",
        "reference/python",
    ):
        try:
            parts = list(relative.relative_to(prefix).with_suffix("").parts)
        except ValueError:
            continue
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    return relative.stem


def _resolve_imports(
    path: str,
    data: bytes,
    modules: dict[str, str],
) -> set[str]:
    tree = ast.parse(data.decode("utf-8"), filename=path)
    importer = _module_for_path(path)
    found: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                base = importer.split(".")[:-1]
                if node.level > 1:
                    base = base[: -(node.level - 1)]
                module = ".".join([*base, module] if module else base)
            names.append(module)
        for name in names:
            candidate = modules.get(name)
            if candidate is not None:
                found.add(candidate)
                parts = name.split(".")
                for index in range(1, len(parts)):
                    parent = modules.get(".".join(parts[:index]))
                    if parent is not None:
                        found.add(parent)
    return found


def runtime_import_closure(
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> list[str]:
    modules = _local_module_map(root)
    replacements = overrides or {}
    closure = set(_BUNDLE_SEEDS)
    pending = list(_BUNDLE_SEEDS)
    while pending:
        relative = pending.pop()
        data = replacements.get(relative)
        if data is None:
            data = (root / relative).read_bytes()
        for imported in _resolve_imports(relative, data, modules):
            if imported not in closure:
                closure.add(imported)
                pending.append(imported)
    return sorted(closure)


def runner_bundle_paths() -> list[str]:
    return runtime_import_closure()


def bundle_digest(
    paths: list[str],
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> str:
    digest = hashlib.sha256()
    replacements = overrides or {}
    for relative in sorted(paths):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        data = replacements.get(relative)
        if data is None:
            data = normalized_bytes(root / relative)
        else:
            data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(data)
    return "sha256:" + digest.hexdigest()


def bundle_manifest_payload(
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    paths = runtime_import_closure(root=root, overrides=overrides)
    replacements = overrides or {}
    entries = []
    for relative in paths:
        data = replacements.get(relative)
        digest = (
            digest_bytes(data)
            if data is not None
            else file_digest(root / relative)
        )
        entries.append(
            {
                "path": relative,
                "role": _BUNDLE_ROLES.get(relative, "runtime_dependency"),
                "digest": digest,
            }
        )
    return {
        "manifest_version": "1.0",
        "entries": entries,
        "bundle_digest": bundle_digest(
            paths,
            root=root,
            overrides=overrides,
        ),
    }


def validate_bundle_manifest(
    manifest: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> list[str]:
    value = manifest if manifest is not None else load_json(BUNDLE_MANIFEST_PATH)
    expected = bundle_manifest_payload(root=root, overrides=overrides)
    errors: list[str] = []
    actual_entries = value.get("entries") if isinstance(value, dict) else None
    if not isinstance(actual_entries, list):
        return ["runner bundle manifest entries are missing"]
    actual_paths = [
        item.get("path") for item in actual_entries if isinstance(item, dict)
    ]
    expected_paths = [item["path"] for item in expected["entries"]]
    missing = sorted(set(expected_paths) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected_paths))
    if missing:
        errors.append("runner bundle has unlisted runtime imports: " + ", ".join(missing))
    if extra:
        errors.append("runner bundle has stale extra paths: " + ", ".join(extra))
    if value != expected:
        errors.append("runner bundle manifest does not match runtime import closure")
    return sorted(set(errors))


def validate_release_registry(
    registry: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    bundle_manifest: dict[str, Any] | None = None,
) -> list[str]:
    value = registry if registry is not None else release_registry()
    errors: list[str] = []
    releases = value.get("releases") if isinstance(value, dict) else None
    if not isinstance(releases, list):
        return ["evidence TCK registry releases are missing"]
    ids = [item.get("release_id") for item in releases if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("evidence TCK release IDs must be unique")
    required_ids = {
        HISTORICAL_TCK_RELEASE_ID,
        TCK_RELEASE_ID,
        PROFILE_TCK_RELEASE_ID,
        PREVIOUS_TCK_RELEASE_ID,
        TCK_1_4_RELEASE_ID,
        TCK_1_5_RELEASE_ID,
        TCK_1_6_RELEASE_ID,
        TCK_1_7_RELEASE_ID,
        TCK_1_8_RELEASE_ID,
        TCK_1_9_RELEASE_ID,
        TCK_1_10_RELEASE_ID,
        CURRENT_TCK_RELEASE_ID,
    }
    if not required_ids.issubset(set(ids)):
        errors.append("evidence TCK registry must retain 1.0.0 through 1.10.0 and register 1.11.0")
    try:
        historical = release_record(HISTORICAL_TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if canonical_digest(historical) != HISTORICAL_RELEASE_RECORD_DIGEST:
            errors.append("evidence TCK 1.0.0 historical record changed")
    supersession = release_supersession(HISTORICAL_TCK_RELEASE_ID, value)
    if not isinstance(supersession, dict):
        errors.append("evidence TCK 1.0.0 supersession metadata is missing")
    else:
        if supersession.get("status") != "superseded-experimental":
            errors.append("evidence TCK 1.0.0 supersession status is inaccurate")
        if supersession.get("frozen_record_digest") != HISTORICAL_RELEASE_RECORD_DIGEST:
            errors.append("evidence TCK 1.0.0 frozen digest metadata is stale")
        if supersession.get("target_registry_schema_digest") != HISTORICAL_TARGET_SCHEMA_DIGEST:
            errors.append("evidence TCK 1.0.0 schema digest metadata is stale")
        if supersession.get("release_registry_digest") != HISTORICAL_RELEASE_REGISTRY_DIGEST:
            errors.append("evidence TCK 1.0.0 release-registry digest metadata is stale")
        if supersession.get("superseded_by") != TCK_RELEASE_ID:
            errors.append("evidence TCK supersession does not point to 1.1.0")

    try:
        projection_release = release_record(TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(projection_release) != FROZEN_TCK_1_1_RECORD_DIGEST:
        errors.append("evidence TCK 1.1.0 frozen record changed")
    projection_target = target_record()
    if projection_release.get("target", {}).get("target_key") != projection_target.target_key:
        errors.append("evidence TCK 1.1.0 target identity changed")
    if projection_release.get("report_schema", {}).get("content_digest") != file_digest(
        root / REPORT_SCHEMA_PATH.relative_to(ROOT)
    ):
        errors.append("evidence report 2.0 bytes differ from frozen TCK 1.1.0")
    legacy_manifest = load_json(root / LEGACY_BUNDLE_MANIFEST_PATH.relative_to(ROOT))
    legacy_bundle = projection_release.get("runner_bundle", {})
    if legacy_bundle.get("manifest_digest") != file_digest(
        root / LEGACY_BUNDLE_MANIFEST_PATH.relative_to(ROOT)
    ):
        errors.append("evidence TCK 1.1.0 frozen bundle manifest changed")
    if legacy_bundle.get("digest") != legacy_manifest.get("bundle_digest"):
        errors.append("evidence TCK 1.1.0 frozen bundle digest changed")

    try:
        profile_release = release_record(PROFILE_TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(profile_release) != FROZEN_TCK_1_2_RECORD_DIGEST:
        errors.append("evidence TCK 1.2.0 frozen record changed")
    frozen_profile_targets = profile_release.get("targets")
    if not isinstance(frozen_profile_targets, list):
        return sorted(set([*errors, "evidence TCK 1.2.0 targets are missing"]))
    frozen_profile_keys = [
        item.get("target_key") for item in frozen_profile_targets if isinstance(item, dict)
    ]
    if len(frozen_profile_keys) != len(set(frozen_profile_keys)):
        errors.append("evidence TCK 1.2.0 target keys must be unique")
    if frozen_profile_keys != list(PROFILE_TARGET_KEYS):
        errors.append("evidence TCK 1.2.0 must contain exactly the three Tier-1 targets")
    frozen_profile_manifest = load_json(
        root / FROZEN_TCK_1_2_BUNDLE_MANIFEST_PATH.relative_to(ROOT)
    )
    frozen_profile_bundle = profile_release.get("runner_bundle", {})
    if frozen_profile_bundle.get("manifest_digest") != file_digest(
        root / FROZEN_TCK_1_2_BUNDLE_MANIFEST_PATH.relative_to(ROOT)
    ):
        errors.append("evidence TCK 1.2.0 frozen bundle manifest changed")
    if frozen_profile_bundle.get("digest") != frozen_profile_manifest.get("bundle_digest"):
        errors.append("evidence TCK 1.2.0 frozen bundle digest changed")

    try:
        previous_release = release_record(PREVIOUS_TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(previous_release) != FROZEN_TCK_1_3_RECORD_DIGEST:
        errors.append("evidence TCK 1.3.0 frozen record changed")
    previous_bundle = previous_release.get("runner_bundle", {})
    if previous_release.get("report_schema", {}).get("content_digest") != (
        FROZEN_TCK_1_3_REPORT_SCHEMA_DIGEST
    ):
        errors.append("evidence TCK 1.3.0 report schema digest changed")
    if previous_release.get("target_registry", {}).get("schema_digest") != (
        FROZEN_TCK_1_3_TARGET_REGISTRY_SCHEMA_DIGEST
    ):
        errors.append("evidence TCK 1.3.0 target registry schema digest changed")
    if previous_release.get("target_registry", {}).get("content_digest") != (
        FROZEN_TCK_1_3_TARGET_REGISTRY_DIGEST
    ):
        errors.append("evidence TCK 1.3.0 target registry digest changed")
    if previous_bundle.get("manifest_digest") != FROZEN_TCK_1_3_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.3.0 bundle manifest digest changed")
    if previous_bundle.get("digest") != FROZEN_TCK_1_3_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.3.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_3_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != (
        FROZEN_TCK_1_3_BUNDLE_MANIFEST_DIGEST
    ):
        errors.append("evidence TCK 1.3.0 bundle manifest bytes changed")
    previous_targets = previous_release.get("targets")
    if not isinstance(previous_targets, list):
        errors.append("evidence TCK 1.3.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get(
                "content_digest"
            )
            for item in previous_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_3_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.3.0 target catalog digests changed")

    try:
        frozen_1_4_release = release_record(TCK_1_4_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(frozen_1_4_release) != FROZEN_TCK_1_4_RECORD_DIGEST:
        errors.append("evidence TCK 1.4.0 frozen record changed")
    frozen_1_4_bundle = frozen_1_4_release.get("runner_bundle", {})
    if frozen_1_4_release.get("report_schema", {}).get("content_digest") != FROZEN_TCK_1_4_REPORT_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.4.0 report schema digest changed")
    if frozen_1_4_release.get("target_registry", {}).get("schema_digest") != FROZEN_TCK_1_4_TARGET_REGISTRY_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.4.0 target registry schema digest changed")
    if frozen_1_4_release.get("target_registry", {}).get("content_digest") != FROZEN_TCK_1_4_TARGET_REGISTRY_DIGEST:
        errors.append("evidence TCK 1.4.0 target registry digest changed")
    if frozen_1_4_bundle.get("manifest_digest") != FROZEN_TCK_1_4_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.4.0 bundle manifest digest changed")
    if frozen_1_4_bundle.get("digest") != FROZEN_TCK_1_4_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.4.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_4_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != FROZEN_TCK_1_4_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.4.0 bundle manifest bytes changed")
    frozen_1_4_targets = frozen_1_4_release.get("targets")
    if not isinstance(frozen_1_4_targets, list):
        errors.append("evidence TCK 1.4.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get("content_digest")
            for item in frozen_1_4_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_4_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.4.0 target catalog digests changed")

    try:
        frozen_1_5_release = release_record(TCK_1_5_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(frozen_1_5_release) != FROZEN_TCK_1_5_RECORD_DIGEST:
        errors.append("evidence TCK 1.5.0 frozen record changed")
    frozen_1_5_bundle = frozen_1_5_release.get("runner_bundle", {})
    if frozen_1_5_release.get("report_schema", {}).get("content_digest") != FROZEN_TCK_1_5_REPORT_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.5.0 report schema digest changed")
    if frozen_1_5_release.get("target_registry", {}).get("schema_digest") != FROZEN_TCK_1_5_TARGET_REGISTRY_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.5.0 target registry schema digest changed")
    if frozen_1_5_release.get("target_registry", {}).get("content_digest") != FROZEN_TCK_1_5_TARGET_REGISTRY_DIGEST:
        errors.append("evidence TCK 1.5.0 target registry digest changed")
    if frozen_1_5_bundle.get("manifest_digest") != FROZEN_TCK_1_5_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.5.0 bundle manifest digest changed")
    if frozen_1_5_bundle.get("digest") != FROZEN_TCK_1_5_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.5.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_5_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != FROZEN_TCK_1_5_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.5.0 bundle manifest bytes changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_binding_trace.schema.json") != FROZEN_TCK_1_5_LIVE_TRACE_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.5.0 live trace v1 schema changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_endpoint_descriptor.schema.json") != FROZEN_TCK_1_5_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.5.0 endpoint descriptor v1 schema changed")
    frozen_1_5_targets = frozen_1_5_release.get("targets")
    if not isinstance(frozen_1_5_targets, list):
        errors.append("evidence TCK 1.5.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get("content_digest")
            for item in frozen_1_5_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_5_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.5.0 target catalog digests changed")

    try:
        frozen_1_6_release = release_record(TCK_1_6_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(frozen_1_6_release) != FROZEN_TCK_1_6_RECORD_DIGEST:
        errors.append("evidence TCK 1.6.0 frozen record changed")
    frozen_1_6_bundle = frozen_1_6_release.get("runner_bundle", {})
    if frozen_1_6_release.get("report_schema", {}).get("content_digest") != FROZEN_TCK_1_6_REPORT_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.6.0 report schema digest changed")
    if frozen_1_6_release.get("target_registry", {}).get("schema_digest") != FROZEN_TCK_1_6_TARGET_REGISTRY_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.6.0 target registry schema digest changed")
    if frozen_1_6_release.get("target_registry", {}).get("content_digest") != FROZEN_TCK_1_6_TARGET_REGISTRY_DIGEST:
        errors.append("evidence TCK 1.6.0 target registry digest changed")
    if frozen_1_6_bundle.get("manifest_digest") != FROZEN_TCK_1_6_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.6.0 bundle manifest digest changed")
    if frozen_1_6_bundle.get("digest") != FROZEN_TCK_1_6_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.6.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_6_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != FROZEN_TCK_1_6_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.6.0 bundle manifest bytes changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_binding_trace_v2.schema.json") != FROZEN_TCK_1_6_LIVE_TRACE_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.6.0 live trace v2 schema changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_endpoint_descriptor_v2.schema.json") != FROZEN_TCK_1_6_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.6.0 endpoint descriptor v2 schema changed")
    frozen_1_6_targets = frozen_1_6_release.get("targets")
    if not isinstance(frozen_1_6_targets, list):
        errors.append("evidence TCK 1.6.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get("content_digest")
            for item in frozen_1_6_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_6_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.6.0 target catalog digests changed")

    try:
        frozen_1_7_release = release_record(TCK_1_7_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(frozen_1_7_release) != FROZEN_TCK_1_7_RECORD_DIGEST:
        errors.append("evidence TCK 1.7.0 frozen record changed")
    frozen_1_7_bundle = frozen_1_7_release.get("runner_bundle", {})
    if frozen_1_7_release.get("report_schema", {}).get("content_digest") != FROZEN_TCK_1_7_REPORT_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.7.0 report schema digest changed")
    if frozen_1_7_release.get("target_registry", {}).get("schema_digest") != FROZEN_TCK_1_7_TARGET_REGISTRY_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.7.0 target registry schema digest changed")
    if frozen_1_7_release.get("target_registry", {}).get("content_digest") != FROZEN_TCK_1_7_TARGET_REGISTRY_DIGEST:
        errors.append("evidence TCK 1.7.0 target registry digest changed")
    if frozen_1_7_bundle.get("manifest_digest") != FROZEN_TCK_1_7_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.7.0 bundle manifest digest changed")
    if frozen_1_7_bundle.get("digest") != FROZEN_TCK_1_7_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.7.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_7_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != FROZEN_TCK_1_7_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.7.0 bundle manifest bytes changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_binding_trace_v3.schema.json") != FROZEN_TCK_1_7_LIVE_TRACE_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.7.0 live trace v3 schema changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_public_scenario_v1.schema.json") != FROZEN_TCK_1_7_PUBLIC_SCENARIO_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.7.0 public scenario schema changed")
    frozen_1_7_targets = frozen_1_7_release.get("targets")
    if not isinstance(frozen_1_7_targets, list):
        errors.append("evidence TCK 1.7.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get("content_digest")
            for item in frozen_1_7_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_7_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.7.0 target catalog digests changed")

    try:
        frozen_1_8_release = release_record(TCK_1_8_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(frozen_1_8_release) != FROZEN_TCK_1_8_RECORD_DIGEST:
        errors.append("evidence TCK 1.8.0 frozen record changed")
    frozen_1_8_bundle = frozen_1_8_release.get("runner_bundle", {})
    if frozen_1_8_release.get("report_schema", {}).get("content_digest") != FROZEN_TCK_1_8_REPORT_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.8.0 report schema digest changed")
    if frozen_1_8_release.get("target_registry", {}).get("schema_digest") != FROZEN_TCK_1_8_TARGET_REGISTRY_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.8.0 target registry schema digest changed")
    if frozen_1_8_release.get("target_registry", {}).get("content_digest") != FROZEN_TCK_1_8_TARGET_REGISTRY_DIGEST:
        errors.append("evidence TCK 1.8.0 target registry digest changed")
    if frozen_1_8_bundle.get("manifest_digest") != FROZEN_TCK_1_8_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.8.0 bundle manifest digest changed")
    if frozen_1_8_bundle.get("digest") != FROZEN_TCK_1_8_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.8.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_8_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != FROZEN_TCK_1_8_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.8.0 bundle manifest bytes changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_binding_trace_v4.schema.json") != FROZEN_TCK_1_8_LIVE_TRACE_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.8.0 live trace v4 schema changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_public_scenario_v1.schema.json") != FROZEN_TCK_1_8_PUBLIC_SCENARIO_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.8.0 public scenario schema changed")
    frozen_1_8_targets = frozen_1_8_release.get("targets")
    if not isinstance(frozen_1_8_targets, list):
        errors.append("evidence TCK 1.8.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get("content_digest")
            for item in frozen_1_8_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_8_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.8.0 target catalog digests changed")

    try:
        frozen_1_9_release = release_record(TCK_1_9_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(frozen_1_9_release) != FROZEN_TCK_1_9_RECORD_DIGEST:
        errors.append("evidence TCK 1.9.0 frozen record changed")
    frozen_1_9_bundle = frozen_1_9_release.get("runner_bundle", {})
    if frozen_1_9_release.get("report_schema", {}).get("content_digest") != FROZEN_TCK_1_9_REPORT_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.9.0 report schema digest changed")
    if frozen_1_9_release.get("target_registry", {}).get("schema_digest") != FROZEN_TCK_1_9_TARGET_REGISTRY_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.9.0 target registry schema digest changed")
    if frozen_1_9_release.get("target_registry", {}).get("content_digest") != FROZEN_TCK_1_9_TARGET_REGISTRY_DIGEST:
        errors.append("evidence TCK 1.9.0 target registry digest changed")
    if frozen_1_9_bundle.get("manifest_digest") != FROZEN_TCK_1_9_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.9.0 bundle manifest digest changed")
    if frozen_1_9_bundle.get("digest") != FROZEN_TCK_1_9_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.9.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_9_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != FROZEN_TCK_1_9_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.9.0 bundle manifest bytes changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_binding_trace_v4.schema.json") != FROZEN_TCK_1_9_LIVE_TRACE_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.9.0 live trace v4 schema changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_public_scenario_v1.schema.json") != FROZEN_TCK_1_9_PUBLIC_SCENARIO_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.9.0 public scenario schema changed")
    frozen_1_9_targets = frozen_1_9_release.get("targets")
    if not isinstance(frozen_1_9_targets, list):
        errors.append("evidence TCK 1.9.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get("content_digest")
            for item in frozen_1_9_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_9_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.9.0 target catalog digests changed")

    try:
        frozen_1_10_release = release_record(TCK_1_10_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(frozen_1_10_release) != FROZEN_TCK_1_10_RECORD_DIGEST:
        errors.append("evidence TCK 1.10.0 frozen record changed")
    frozen_1_10_bundle = frozen_1_10_release.get("runner_bundle", {})
    if frozen_1_10_release.get("report_schema", {}).get("content_digest") != FROZEN_TCK_1_10_REPORT_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.10.0 report schema digest changed")
    if frozen_1_10_release.get("target_registry", {}).get("schema_digest") != FROZEN_TCK_1_10_TARGET_REGISTRY_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.10.0 target registry schema digest changed")
    if frozen_1_10_release.get("target_registry", {}).get("content_digest") != FROZEN_TCK_1_10_TARGET_REGISTRY_DIGEST:
        errors.append("evidence TCK 1.10.0 target registry digest changed")
    if frozen_1_10_bundle.get("manifest_digest") != FROZEN_TCK_1_10_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.10.0 bundle manifest digest changed")
    if frozen_1_10_bundle.get("digest") != FROZEN_TCK_1_10_RUNNER_BUNDLE_DIGEST:
        errors.append("evidence TCK 1.10.0 runner bundle digest changed")
    if file_digest(root / FROZEN_TCK_1_10_BUNDLE_MANIFEST_PATH.relative_to(ROOT)) != FROZEN_TCK_1_10_BUNDLE_MANIFEST_DIGEST:
        errors.append("evidence TCK 1.10.0 bundle manifest bytes changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_binding_trace_v4.schema.json") != FROZEN_TCK_1_10_LIVE_TRACE_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.10.0 live trace v4 schema changed")
    if file_digest(root / "conformance/evidence/live_bindings/live_public_scenario_v1.schema.json") != FROZEN_TCK_1_10_PUBLIC_SCENARIO_SCHEMA_DIGEST:
        errors.append("evidence TCK 1.10.0 public scenario schema changed")
    frozen_1_10_targets = frozen_1_10_release.get("targets")
    if not isinstance(frozen_1_10_targets, list):
        errors.append("evidence TCK 1.10.0 targets are missing")
    else:
        observed_catalogs = {
            str(item.get("target_key")): (item.get("target_catalog") or {}).get("content_digest")
            for item in frozen_1_10_targets
            if isinstance(item, dict)
        }
        if observed_catalogs != FROZEN_TCK_1_10_TARGET_CATALOG_DIGESTS:
            errors.append("evidence TCK 1.10.0 target catalog digests changed")

    try:
        current_release = release_record(CURRENT_TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    release_targets = current_release.get("targets")
    if not isinstance(release_targets, list):
        return sorted(set([*errors, "evidence TCK 1.11.0 targets are missing"]))
    release_keys = [
        item.get("target_key") for item in release_targets if isinstance(item, dict)
    ]
    if len(release_keys) != len(set(release_keys)):
        errors.append("evidence TCK 1.11.0 target keys must be unique")
    if release_keys != list(EXPECTED_TARGET_KEYS):
        errors.append("evidence TCK 1.11.0 must contain all six generalized targets")
    expected_checks = {
        current_release.get("report_schema", {}).get("content_digest"): file_digest(
            root / REPORT_SCHEMA_V22_PATH.relative_to(ROOT)
        ),
        current_release.get("target_registry", {}).get("content_digest"): file_digest(
            root / TARGETS_PATH.relative_to(ROOT)
        ),
        current_release.get("target_registry", {}).get("schema_digest"): file_digest(
            root / TARGET_SCHEMA_PATH.relative_to(ROOT)
        ),
    }
    if any(actual != expected for actual, expected in expected_checks.items()):
        errors.append("evidence TCK 1.11.0 common provenance does not match current bytes")
    manifest = bundle_manifest or load_json(root / BUNDLE_MANIFEST_PATH.relative_to(ROOT))
    errors.extend(validate_bundle_manifest(manifest, root=root))
    runner_bundle = current_release.get("runner_bundle", {})
    if runner_bundle.get("manifest_path") != BUNDLE_MANIFEST_PATH.relative_to(ROOT).as_posix():
        errors.append("evidence TCK 1.11.0 runner bundle manifest path is incorrect")
    if runner_bundle.get("manifest_digest") != file_digest(root / BUNDLE_MANIFEST_PATH.relative_to(ROOT)):
        errors.append("evidence TCK 1.11.0 runner bundle manifest digest is stale")
    if runner_bundle.get("digest") != manifest.get("bundle_digest"):
        errors.append("evidence TCK 1.11.0 runner bundle digest is stale")
    if runner_bundle.get("paths") != [item["path"] for item in manifest.get("entries", [])]:
        errors.append("evidence TCK 1.11.0 runner bundle paths do not match manifest")

    expected_policies = {
        HISTORICAL_TCK_RELEASE_ID: False,
        TCK_RELEASE_ID: True,
        PROFILE_TCK_RELEASE_ID: False,
        PREVIOUS_TCK_RELEASE_ID: False,
        TCK_1_4_RELEASE_ID: True,
        TCK_1_5_RELEASE_ID: False,
        TCK_1_6_RELEASE_ID: False,
        TCK_1_7_RELEASE_ID: False,
        TCK_1_8_RELEASE_ID: True,
        TCK_1_9_RELEASE_ID: False,
        TCK_1_10_RELEASE_ID: True,
        CURRENT_TCK_RELEASE_ID: True,
    }
    for release_id, eligible in expected_policies.items():
        try:
            policy = release_policy(release_id, value)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if policy.get("strong_eligible") is not eligible:
            errors.append(f"evidence TCK strong-eligibility policy is inaccurate: {release_id}")
        if not isinstance(policy.get("reason"), str) or not policy.get("reason"):
            errors.append(f"evidence TCK release policy reason is missing: {release_id}")

    snapshot_expectations = {
        TCK_RELEASE_ID: FROZEN_TCK_1_1_REGISTRY_SNAPSHOT_DIGEST,
        PROFILE_TCK_RELEASE_ID: FROZEN_TCK_1_2_REGISTRY_SNAPSHOT_DIGEST,
        PREVIOUS_TCK_RELEASE_ID: FROZEN_TCK_1_3_REGISTRY_SNAPSHOT_DIGEST,
        TCK_1_4_RELEASE_ID: FROZEN_TCK_1_4_REGISTRY_SNAPSHOT_DIGEST,
        TCK_1_5_RELEASE_ID: FROZEN_TCK_1_5_REGISTRY_SNAPSHOT_DIGEST,
        TCK_1_6_RELEASE_ID: FROZEN_TCK_1_6_REGISTRY_SNAPSHOT_DIGEST,
        TCK_1_7_RELEASE_ID: FROZEN_TCK_1_7_REGISTRY_SNAPSHOT_DIGEST,
        TCK_1_8_RELEASE_ID: FROZEN_TCK_1_8_REGISTRY_SNAPSHOT_DIGEST,
        TCK_1_9_RELEASE_ID: FROZEN_TCK_1_9_REGISTRY_SNAPSHOT_DIGEST,
        TCK_1_10_RELEASE_ID: FROZEN_TCK_1_10_REGISTRY_SNAPSHOT_DIGEST,
    }
    for release_id in (
        TCK_RELEASE_ID,
        PROFILE_TCK_RELEASE_ID,
        PREVIOUS_TCK_RELEASE_ID,
        TCK_1_4_RELEASE_ID,
        TCK_1_5_RELEASE_ID,
        TCK_1_6_RELEASE_ID,
        TCK_1_7_RELEASE_ID,
        TCK_1_8_RELEASE_ID,
        TCK_1_9_RELEASE_ID,
        TCK_1_10_RELEASE_ID,
        CURRENT_TCK_RELEASE_ID,
    ):
        try:
            snapshot = release_snapshot(release_id)
            snapshot_record = release_record(release_id, snapshot)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        expected_snapshot_digest = snapshot_expectations.get(release_id)
        if expected_snapshot_digest and release_snapshot_digest(release_id) != expected_snapshot_digest:
            errors.append(f"evidence TCK release snapshot changed: {release_id}")
        if canonical_digest(snapshot_record) != canonical_digest(release_record(release_id, value)):
            errors.append(f"evidence TCK release snapshot record differs from registry: {release_id}")

    for record in [resolve_target_record(key) for key in EXPECTED_TARGET_KEYS]:
        try:
            selected_release = release_record(record.current_release_id, value)
            selected_target = release_target_entry(selected_release, record.target_key)
        except ValueError as exc:
            errors.append(f"target/release resolution failed: {record.target_key}: {exc}")
            continue
        catalog_value = target_catalog(record)
        if selected_target.get("handler_id") != record.handler_id:
            errors.append(f"release handler mismatch: {record.target_key}")
        if selected_target.get("expected_mark") != record.expected_mark:
            errors.append(f"release mark mismatch: {record.target_key}")
        if selected_target.get("target_catalog", {}).get("path") != record.catalog_path:
            errors.append(f"release target catalog path mismatch: {record.target_key}")
        if selected_target.get("target_catalog", {}).get("content_digest") != file_digest(
            root / record.catalog_path
        ):
            errors.append(f"release target catalog digest is stale: {record.target_key}")
        expected_suite_paths = list(record.required_suites)
        suites = expected_suite_records(selected_release, record.target_key)
        if [item["path"] for item in suites] != expected_suite_paths:
            errors.append(f"release required suites mismatch: {record.target_key}")
        for item in suites:
            if file_digest(root / item["path"]) != item["suite_digest"]:
                errors.append(f"evidence TCK suite digest is stale: {item['path']}")
        for item in expected_input_artifacts(selected_release, record.target_key):
            if file_digest(root / item["path"]) != item["content_digest"]:
                errors.append(f"evidence TCK input digest is stale: {item['path']}")
        try:
            from target_handlers import resolve_handler

            handler = resolve_handler(record.handler_id)
            expected_ids = mandatory_case_ids(
                catalog_value,
                record.execution_mode,
                handler,
            )
        except (ImportError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"release mandatory-case resolution failed: {record.target_key}: {exc}")
        else:
            if "mandatory_case_ids" in selected_target:
                if selected_target.get("mandatory_case_ids") != expected_ids:
                    errors.append(f"release mandatory case IDs are stale: {record.target_key}")
            else:
                producer_ids = [
                    str(item["case_id"])
                    for item in handler.producer_cases(
                        catalog_value,
                        record.execution_mode,
                    )
                ]
                consumer_ids = [
                    str(item["case_id"])
                    for item in handler.consumer_cases(
                        catalog_value,
                        record.execution_mode,
                    )
                ]
                if selected_target.get("mandatory_producer_ids") != producer_ids:
                    errors.append(f"release mandatory producer IDs are stale: {record.target_key}")
                if selected_target.get("mandatory_consumer_ids") != consumer_ids:
                    errors.append(f"release mandatory consumer IDs are stale: {record.target_key}")
    return sorted(set(errors))
