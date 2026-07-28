export type VersionHash = {
  version: string;
  contract_hash: string;
};

export type ExactContractReference = {
  branch_id: string;
  base?: VersionHash;
  head: VersionHash;
};

export type AgreementIssue = {
  code: string;
  message: string;
  index: number;
};

export type AgreementReductionOptions = {
  invalidIndices?: Iterable<number>;
};

export {
  ACCEPT_BINDING,
  ACTIVE_HEAD,
  AGREEMENT_STATE,
  CONFLICT_BINDING,
  CONTEXT_BINDING,
  CONTRACT_HASH,
  CONTRACT_ID,
  CONTRACT_REF,
  CONTRACT_SCHEMA,
  PROPOSAL_BINDING,
  buildAcceptanceBinding,
  buildProposalBinding,
  chooseResolution,
  computeContractHash,
  currentHeadReference,
  proposalCandidate,
  reduceTranscript,
  semanticIssueIds,
  validateContractReference,
} from "./contract_agreement.js";
