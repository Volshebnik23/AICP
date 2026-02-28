# Chat rules (deterministic simulation policy)

## Chat purpose
Demonstrate protocol-level mediated enforcement behavior with safe placeholders and deterministic outcomes.

## Rule categories + markers
1. **Brand safety**: disallow `[VIOLATION:BRAND_OFF_POLICY]`
2. **PII/compliance**: disallow `[VIOLATION:PII_EMAIL]`, `[VIOLATION:PII_PHONE]`
3. **Prompt-injection / policy bypass**: disallow `[VIOLATION:PROMPT_INJECTION]`
4. **Malware/social engineering**: disallow `[VIOLATION:MALWARE]`, `[VIOLATION:PHISHING]`
5. **Harassment/toxicity**: disallow `[VIOLATION:HARASSMENT]`
6. **Spam/abuse**: disallow `[VIOLATION:SPAM]`

## Escalation policy
- First violation by actor in session: `DENY + WARN` and `ALERT(code=POLICY_DENIED, severity=WARNING, recommended_actions=[REMEDIATE, ACK_REQUIRED])`.
- Second violation by same actor in session: `DENY + KICK` and `ALERT(code=SANCTION_APPLIED, severity=FATAL, recommended_actions=[DISCONNECT])`.

## Safety note
Markers are placeholders to keep repository content safe. Real deployments would use classifiers/policy engines and richer enforcement logic.
