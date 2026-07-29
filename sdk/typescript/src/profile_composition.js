import { objectHash } from "./hashing.js";

export const COMPOSITION_VERSION = "aicp.profile_composition.v1";
export const COMPOSITION_HASH_DOMAIN = "capneg.profile_composition";

export function canonicalProfileRefKey(value) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return ["", ""];
  }
  return [String(value.profile_id ?? ""), String(value.profile_version ?? "")];
}

function compareProfileRefs(left, right) {
  const [leftId, leftVersion] = canonicalProfileRefKey(left);
  const [rightId, rightVersion] = canonicalProfileRefKey(right);
  return leftId.localeCompare(rightId) || leftVersion.localeCompare(rightVersion);
}

function profileKey(value) {
  return canonicalProfileRefKey(value).join("\0");
}

function error(code, detail) {
  return { code, detail };
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

export function resolveProfileComposition(compositionValue, rules) {
  let composition = compositionValue;
  const errors = [];
  if (composition === null || typeof composition !== "object" || Array.isArray(composition)) {
    composition = {};
    errors.push(error("PROFILE_COMPOSITION_SHAPE_INVALID", "profile composition must be an object"));
  }
  if (composition.composition_version !== COMPOSITION_VERSION) {
    errors.push(
      error(
        "PROFILE_COMPOSITION_VERSION_UNSUPPORTED",
        `composition_version must equal ${COMPOSITION_VERSION}`,
      ),
    );
  }
  let rawProfiles = composition.profiles;
  if (!Array.isArray(rawProfiles)) {
    rawProfiles = [];
    errors.push(error("PROFILE_COMPOSITION_SHAPE_INVALID", "profiles must be an array"));
  }
  if (rawProfiles.length === 0) {
    errors.push(
      error("PROFILE_COMPOSITION_EMPTY", "profile composition must contain at least one profile"),
    );
  }
  const maximum = Number(rules.maximum_profiles ?? 16);
  if (rawProfiles.length > maximum) {
    errors.push(
      error(
        "PROFILE_COMPOSITION_LIMIT_EXCEEDED",
        `profile composition exceeds maximum_profiles=${maximum}`,
      ),
    );
  }
  const validShape = rawProfiles.every(
    (profile) =>
      profile !== null &&
      typeof profile === "object" &&
      !Array.isArray(profile) &&
      Object.keys(profile).sort().join(",") === "profile_id,profile_version" &&
      typeof profile.profile_id === "string" &&
      profile.profile_id.length > 0 &&
      typeof profile.profile_version === "string" &&
      profile.profile_version.length > 0,
  );
  if (!validShape) {
    errors.push(
      error(
        "PROFILE_REF_INVALID",
        "every profile must contain only non-empty profile_id and profile_version",
      ),
    );
  }

  const canonicalProfiles = clone(rawProfiles).sort(compareProfileRefs);
  const canonicalComposition = {
    composition_version: COMPOSITION_VERSION,
    profiles: canonicalProfiles,
  };
  if (JSON.stringify(rawProfiles) !== JSON.stringify(canonicalProfiles)) {
    errors.push(
      error(
        "PROFILE_ORDER_NON_CANONICAL",
        "profiles must be sorted by exact profile_id then profile_version",
      ),
    );
  }
  const keys = rawProfiles.map(profileKey);
  for (const key of [...new Set(keys.filter((candidate) => keys.filter((value) => value === candidate).length > 1))].sort()) {
    const [profileId, profileVersion] = key.split("\0");
    errors.push(
      error("PROFILE_DUPLICATE", `duplicate profile reference ${profileId}@${profileVersion}`),
    );
  }
  const versionsById = new Map();
  for (const profile of rawProfiles) {
    const [profileId, profileVersion] = canonicalProfileRefKey(profile);
    if (!versionsById.has(profileId)) versionsById.set(profileId, new Set());
    versionsById.get(profileId).add(profileVersion);
  }
  for (const profileId of [...versionsById.keys()].sort()) {
    const versions = [...versionsById.get(profileId)].sort();
    if (versions.length > 1) {
      errors.push(
        error(
          "PROFILE_FAMILY_VERSION_CONFLICT",
          `${profileId} selects multiple exact versions: ${JSON.stringify(versions)}`,
        ),
      );
    }
  }

  const records = new Map(
    (rules.profiles ?? []).map((record) => [profileKey(record.profile), record]),
  );
  const selectedRecords = [];
  for (const key of [...new Set(keys)].sort()) {
    const record = records.get(key);
    if (record === undefined) {
      const [profileId, profileVersion] = key.split("\0");
      errors.push(error("PROFILE_UNKNOWN", `unknown exact profile ${profileId}@${profileVersion}`));
    } else {
      selectedRecords.push(record);
    }
  }
  const corePaths = [
    ...new Set(selectedRecords.map((record) => record.core_suite?.path ?? "")),
  ].sort();
  if (corePaths.length > 1) {
    errors.push(
      error(
        "PROFILE_CORE_VERSION_CONFLICT",
        `selected profiles resolve to multiple Core suites: ${JSON.stringify(corePaths)}`,
      ),
    );
  }
  for (const record of selectedRecords) {
    if (record.negotiable_by_capneg_v0_2 !== true) {
      const reason = record.capneg_v0_2_unsupported_reason ?? {};
      errors.push(
        error(
          String(reason.reason_code ?? "CAPNEG_CORE_FAMILY_UNSUPPORTED"),
          String(reason.detail ?? "profile is not negotiable by CAPNEG v0.2"),
        ),
      );
    }
  }
  const selectedKeys = new Set(keys);
  for (const relation of rules.rules?.strict_suite_subset_relations ?? []) {
    const redundant = profileKey(relation.redundant_profile);
    const covering = profileKey(relation.covering_profile);
    if (selectedKeys.has(redundant) && selectedKeys.has(covering)) {
      const [redundantId, redundantVersion] = redundant.split("\0");
      const [coveringId, coveringVersion] = covering.split("\0");
      errors.push(
        error(
          "PROFILE_COMPOSITION_REDUNDANT",
          `${redundantId}@${redundantVersion} is a strict required-suite subset of ${coveringId}@${coveringVersion}`,
        ),
      );
    }
  }
  for (const group of rules.rules?.exclusive_groups ?? []) {
    const members = new Set((group.members ?? []).map(profileKey));
    const selected = [...selectedKeys].filter((key) => members.has(key)).sort();
    const maxSelected = Number(group.max_selected ?? 1);
    if (selected.length > maxSelected) {
      errors.push(
        error(
          "PROFILE_COMPOSITION_EXCLUSIVE_CONFLICT",
          `exclusive group ${group.group_id} allows at most ${maxSelected}`,
        ),
      );
    }
  }
  const union = (field) =>
    [
      ...new Set(
        selectedRecords.flatMap((record) =>
          (record[field] ?? []).filter((value) => typeof value === "string"),
        ),
      ),
    ].sort();
  const componentMarks = [
    ...new Set(
      selectedRecords
        .map((record) => record.compatibility_mark)
        .filter((value) => typeof value === "string"),
    ),
  ].sort();
  return {
    composition: canonicalComposition,
    composition_hash:
      errors.length === 0
        ? objectHash(COMPOSITION_HASH_DOMAIN, canonicalComposition)
        : null,
    core_suite:
      corePaths.length === 1 && selectedRecords.length > 0
        ? clone(selectedRecords[0].core_suite)
        : null,
    required_suites: union("required_suites"),
    required_extensions: union("required_extensions"),
    required_crypto_profiles: union("required_crypto_profiles"),
    required_policy_categories: union("required_policy_categories"),
    component_compatibility_marks: componentMarks,
    errors,
  };
}
