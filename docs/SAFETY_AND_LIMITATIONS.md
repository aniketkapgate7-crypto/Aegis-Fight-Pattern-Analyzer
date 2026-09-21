# Safety, Privacy, and Ethical Limitations

## 1. Fundamental Scope & Purpose

**Aegis** is an on-device motion intelligence system developed for real-time human pose and temporal movement analysis on Snapdragon-powered HP PCs. Its engineering objective is to extract explainable biomechanical movement patterns—such as strikes, defensive postures, rapid approach, and falls—without relying on cloud connectivity, biometric identification, or facial processing.

> [!IMPORTANT]
> **Aegis detects motion patterns, not human intent.** Movement trajectories that resemble a punch, kick, or rapid approach may arise in martial arts sparring, athletic conditioning, stunt performance, dramatic arts, or non-aggressive physical interactions. Aegis provides descriptive kinematic signals; it does not and cannot infer motive, guilt, malice, or intent.

---

## 2. Privacy-by-Design Safeguards

1. **No Facial Recognition or Biometrics**: Aegis does not perform face recognition, face identification, facial embeddings or biometric identity tracking. One coarse nose keypoint is used only for pose geometry.
2. **No Identity Database**: Aegis operates completely anonymously. It maintains no user profiles, registry of persons, demographic classification, or identity tracking.
3. **100% Local On-Device Processing**: Video stream frames are analysed entirely in local memory (RAM) on the host machine. Frame buffers are processed instantaneously and overwritten. No video, audio, or metadata is ever transmitted over network interfaces or uploaded to cloud endpoints.
4. **Optional Local Logging**: Incident recording is strictly opt-in and controlled via manual operator toggle (`R` or `Space`). Event logs (`artifacts/incidents.jsonl`) reside exclusively in local storage on the host machine and are never synchronized externally.
5. **Synthetic Demonstration Mode**: A deterministic synthetic mode (`--demo` and `--export-preview`) allows complete testing, documentation, and evaluation without activating an optical sensor or exposing private physical spaces.

---

## 3. Human-in-the-Loop Requirement & Non-Autonomous Enforcement

- **Decision-Support Only**: Aegis is engineered solely as a human-in-the-loop decision-support tool. It provides contextual, explainable telemetry (visual threat gauge, kinematic evidence, and event timeline) to assist trained human operators.
- **Strict Prohibition of Autonomous Action**: Under no circumstances should Aegis outputs trigger automated physical interlocks, disciplinary mechanisms, algorithmic penalties, or autonomous enforcement actions.
- **Human Review Mandatory**: All detections require contextual verification by qualified human evaluators. Aegis must never serve as the sole or primary basis for legal, disciplinary, employment, or safety-critical determinations.

---

## 4. Technical Constraints & Failure Modes

Aegis relies on vision-based landmark estimation followed by temporal rule evaluation. Operators must be aware of operational factors that can degrade performance or produce false positives/negatives:

- **Severe Occlusion**: Physical obstructions (furniture, pillars, crowd density) that conceal key torso or limb landmarks prevent reliable pattern recognition and trigger fail-safe neutral classification.
- **Challenging Lighting**: Extreme underexposure, intense backlight, lens flare, or strobe illumination can degrade landmark coordinate precision.
- **Extreme Camera Perspectives**: Camera placements with steep overhead angles (top-down surveillance) or extreme low angles distort 2D planar projections of shoulder width and torso aspect ratios.
- **Unusual or Non-Combat Movements**: Rapid celebratory gestures, tumbling, dancing, breakdancing, high-velocity sports actions (e.g., volleyball spiking, gymnastics), or sudden trips may exhibit kinematic similarity to combat extensions or fall patterns.
- **Loose or Voluminous Clothing**: Heavy garments, coats, robes, or props can obscure joint articulations, leading to spatial landmark jitter.

---

## 5. Intended and Permitted Use Cases

- **Athletic & Combat Sports Coaching**: Quantitative feedback on strike extension velocity, guard consistency, and defensive readiness in boxing, karate, taekwondo, and mixed martial arts training.
- **Supervised Safety Evaluation**: Assisting venue safety personnel in monitoring public athletic events or physical conditioning facilities with human oversight.
- **Academic & Edge AI Research**: Demonstration and benchmark evaluation of privacy-preserving on-device computer vision and NPU acceleration architectures.

---

## 6. Prohibited and Out-of-Scope Uses

- Autonomous weapon or defensive turret targeting.
- Unsupervised law enforcement or penal monitoring.
- Covert or non-consensual biometric surveillance.
- Workplace productivity tracking or employee monitoring.
- Automated generation of criminal or disciplinary charges without independent evidence.
