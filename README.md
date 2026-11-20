# Secure Fingerprint Authentication System (ZeroBio Vault)
### Biometric Cryptosystem using Juels-Wattenberg Fuzzy Commitment & Schnorr 3-Pass Zero-Knowledge Proof (ZKP)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Dataset: Kaggle SOCOFing](https://img.shields.io/badge/Dataset-Kaggle_SOCOFing-orange.svg)](https://www.kaggle.com/datasets/ruizgara/socofing)
[![Security: Zero Biometric Leakage](https://img.shields.io/badge/Security-Zero_Biometric_Leakage-emerald.svg)](#privacy--zero-biometric-leakage)

---

## 📌 Executive Summary

This project delivers a complete, secure biometric authentication project conforming strictly to the provided architectural flow diagram:
- **Enrollment Phase (Sign Up):** Captures fingerprint images, performs normalization, Gabor filtering, and skeletonization, extracts minutiae, generates a 1024-bit canonical binary template $B$, binds it to an ephemeral 64-bit secret key $C$ using an Error-Correcting Code (ECC) to produce helper data $W = B \oplus \text{Codeword}(C)$, computes commitment $H = \text{SHA-256}(C)$ and public key $Y = g^C \pmod p$, and saves **only $(W, H, Y)$** to the database.
- **Authentication Phase (Login):** Preprocesses the query fingerprint, extracts query template $B'$, computes noisy codeword $B' \oplus W$, performs Hadamard-128 error correction to recover $C'$, verifies the decision diamond $\text{SHA-256}(C') \stackrel{?}{=} H$, and executes the interactive **Schnorr 3-Pass Zero-Knowledge Proof** before granting access.
- **Dataset:** Kaggle SOCOFing. The full run uses all 600 subjects, split 80% train and 20% test by person. A genuine try is the same finger after rotation, smudging, or a cut. An impostor try is a different person.
- **Measured scores** are stored in `data/evaluation_results.json` and shown on the website. On the fresh test group: EER 1.539%, cryptographic FAR 0.177%, cryptographic FRR 4.466%, AUC 0.996.
- **Simple, Aesthetic Web Interface:** A minimalist, modern UI (Apple/Linear design aesthetic) featuring 1-click genuine/impostor demos, sample presets, live verification result cards with collapsible cryptographic proofs, and interactive dataset benchmark graphs.

---

## 🏗️ System Architecture & Flow Diagram

The implementation directly realizes every block of the system flow diagram:

```
========================================================================================
   ENROLLMENT (SIGN UP)                                 AUTHENTICATION (LOGIN)
========================================================================================
1. Input: Fingerprint Image                           1. Input: Fingerprint Image (Query)
          │                                                     │
2. Preprocessing (Norm, Filter, Thin)                 2. Preprocessing (Same as Enrollment)
          │                                                     │
3. Feature Extraction (Minutiae & Core)               3. Feature Extraction (Minutiae & Core)
          │                                                     │
4. Template Generation (Binary B in {0,1}^1024)       4. Template Generation (Query B')
          │                                                     │
5. Fuzzy Commitment (With Secret Key C):              5. Fuzzy Recovery (Recover Secret Key):
   - Generate random secret key (C)                      - Noisy codeword = B' XOR W
   - ECC encode C -> Codeword(C)                         - ECC error-correct to get C'
   - Helper data W = B XOR Codeword(C)                   - Check if SHA256(C') == H
   - Commitment H = SHA256(C)                                   │
   - Public key Y = g^C mod p                            [ Is SHA256(C') == H ? ]
          │                                                /                 \
6. Store in Database (ONLY W, H, Y)                       No                 Yes
          │                                               │                   │
      [DATABASE]                                    ACCESS DENIED   6. Schnorr ZKP (3-Pass)
   (Stores only W,H,Y)                                              - Commitment: t = g^r mod p
          │                                                         - Challenge:  c (random)
          └─────────────────────────────────────────────────────────- Response:   s = r + c*x mod q
                                                                    - Verify:     g^s == t * Y^c mod p
                                                                              │
                                                                    7. Verification Result:
                                                                       ACCESS GRANTED / DENIED
========================================================================================
```

---


## 🚀 Getting Started & Running the Project

### 1. Prerequisites & Environment Setup
Clone or navigate to the project directory:
```bash
cd c:\Users\chhim\Downloads\UROP_FINALEv
```
Install dependencies (OpenCV, FastAPI, Uvicorn, Jinja2, Matplotlib, Scikit-learn):
```bash
pip install -r requirements.txt
```

### 2. Launch the Web Interface
Start the modern aesthetic web dashboard:
```bash
python -m uvicorn web.app:app --host 127.0.0.1 --port 8000 --reload
```
Open **`http://127.0.0.1:8000`** in any web browser to view the interface.

**Features of the Webpage:**
- **One-Click Instant Demos:** Test genuine access grant or impostor attack rejection with one click.
- **2-Step Flow:** Clean Enroll (Sign Up) and Authenticate (Login) cards with sample presets.
- **Result Banner:** Large aesthetic status card showing Hamming distance error, ECC recovery state, SHA-256 hash match, and Schnorr ZKP verification.
- **Collapsible Inspector:** View preprocessed minutiae overlay and exact 3-pass Schnorr parameters ($t, c, s$).
- **Benchmark Viewer:** SOCOFing training group and fresh test group, with the measured error rates and charts.
- **Privacy Audit:** Live database inspection proving only $W, H, Y$ are saved.

### 3. Run Command-Line Demo (CLI)
You can also run the interactive terminal demo:
```bash
python run_demo.py
```

### 4. Run Automated Test Suite
Execute the pytest suite (15 unit & integration tests covering preprocessing, minutiae extraction, fuzzy commitment, Schnorr ZKP, and end-to-end authentication):
```bash
pytest -v
```

### 5. Re-run Dataset Evaluation & Generate Plots
To re-evaluate the datasets and regenerate ROC curve plots:
```bash
python evaluation/evaluate_dataset.py
```
The SOCOFing charts are saved with the results file and shown on the website.

---

## 🔒 Privacy & Zero Biometric Leakage Guarantee

The database stores **only 3 cryptographic values per user**:
1. **Helper Data ($W$):** 1024-bit vector defined as $W = B \oplus \text{Codeword}(C)$. Information-theoretically secure against template inversion without knowledge of secret key $C$.
2. **Hash Commitment ($H$):** Standard 256-bit SHA-256 digest $H = \text{SHA-256}(C)$. One-way preimage resistant.
3. **Schnorr Public Key ($Y$):** 1024-bit modular exponentiation $Y = g^C \pmod p$. Computational discrete logarithm problem prevents extraction of $C$.

> **Zero Leakage Invariant:** No raw images, no minutiae $(x, y, \theta)$ coordinates, no binary templates $B$, and no secret keys $C$ are ever written to the database or persisted on disk. Database theft yields zero reconstructible biometric information.

---

## 🏗️ System Architecture & Flow Diagram

The implementation directly realizes every block of the system flow diagram:

```
========================================================================================
   ENROLLMENT (SIGN UP)                                 AUTHENTICATION (LOGIN)
========================================================================================
1. Input: Fingerprint Image                           1. Input: Fingerprint Image (Query)
          │                                                     │
2. Preprocessing (Norm, Filter, Thin)                 2. Preprocessing (Same as Enrollment)
          │                                                     │
3. Feature Extraction (Minutiae & Core)               3. Feature Extraction (Minutiae & Core)
          │                                                     │
4. Template Generation (Binary B in {0,1}^1024)       4. Template Generation (Query B')
          │                                                     │
5. Fuzzy Commitment (With Secret Key C):              5. Fuzzy Recovery (Recover Secret Key):
   - Generate random secret key (C)                      - Noisy codeword = B' XOR W
   - ECC encode C -> Codeword(C)                         - ECC error-correct to get C'
   - Helper data W = B XOR Codeword(C)                   - Check if SHA256(C') == H
   - Commitment H = SHA256(C)                                   │
   - Public key Y = g^C mod p                            [ Is SHA256(C') == H ? ]
          │                                                /                 \
6. Store in Database (ONLY W, H, Y)                       No                 Yes
          │                                               │                   │
      [DATABASE]                                    ACCESS DENIED   6. Schnorr ZKP (3-Pass)
   (Stores only W,H,Y)                                              - Commitment: t = g^r mod p
          │                                                         - Challenge:  c (random)
          └─────────────────────────────────────────────────────────- Response:   s = r + c*x mod q
                                                                    - Verify:     g^s == t * Y^c mod p
                                                                              │
                                                                    7. Verification Result:
                                                                       ACCESS GRANTED / DENIED
========================================================================================
```

---

## 🔬 Mathematical Formulations

### 1. Preprocessing & Minutiae Extraction
- **Contrast Normalization:**
  $$I'(x, y) = \begin{cases} M_0 + \sqrt{\frac{V_0(I(x, y) - M)^2}{V}} & \text{if } I(x, y) > M \\ M_0 - \sqrt{\frac{V_0(I(x, y) - M)^2}{V}} & \text{otherwise} \end{cases}$$
  with $M_0 = 128, V_0 = 2500$.
- **2D Gabor Filter Bank:**
  $$G(x, y; \theta, f) = \exp\left(-\frac{1}{2}\left(\frac{x_\theta^2}{\sigma_x^2} + \frac{y_\theta^2}{\sigma_y^2}\right)\right) \cos(2\pi f x_\theta)$$
  convolved across 8 directions $\theta \in \{0, \frac{\pi}{8}, \dots, \frac{7\pi}{8}\}$.
- **Crossing Number (CN) on Skeleton:**
  $$CN(P) = \frac{1}{2} \sum_{i=1}^{8} |P_i - P_{i+1}|, \quad P_9 = P_1$$
  - $CN = 1$: Ridge Ending (Termination)
  - $CN = 3$: Ridge Bifurcation

### 2. Juels-Wattenberg Fuzzy Commitment Scheme
- Biometric template $B \in \{0, 1\}^{1024}$.
- Ephemeral cryptographic secret $C \in \{0, 1\}^{64}$.
- Error-Correcting Code $\text{ECC}: \{0, 1\}^{64} \to \{0, 1\}^{1024}$.
- Helper data:
  $$W = B \oplus \text{Codeword}(C)$$
- Commitment:
  $$H = \text{SHA-256}(C)$$
- During authentication with query template $B'$:
  $$\text{NoisyCodeword} = B' \oplus W = (B' \oplus B) \oplus \text{Codeword}(C)$$
  If the Hamming distance $d_H(B, B') \le t_{\text{ECC}}$, the decoder successfully recovers $C' = C$.

### 3. Hadamard-128 Error-Correcting Code
- Message length: 8 bytes (64 bits).
- Codeword length: $8 \times 128 = 1024$ bits.
- Minimum distance: $d_{\min} = 64$.
- Error correction capability: Up to 31 bit flips per 128-bit block ($24.2\%$ error rate).
- Decoded using Maximum Likelihood Fast Walsh-Hadamard Transform correlation:
  $$\hat{c}_i = \arg\max_{j} |\langle \mathbf{v}_i, H_{128}[j] \rangle|$$

### 4. Interactive Schnorr 3-Pass Zero-Knowledge Proof
- Group parameters: RFC 5114 1024-bit MODP prime $p$, subgroup prime order $q = (p-1)/2$, generator $g = 2$.
- Private key: $x = \text{int}(C) \pmod q$.
- Public key: $Y = g^x \pmod p$.
- **Pass 1 (Commitment):** Prover chooses ephemeral nonce $r \in_R \mathbb{Z}_q^*$, computes $t = g^r \pmod p$, sends $t$ to Verifier.
- **Pass 2 (Challenge):** Verifier generates random challenge $c \in_R \mathbb{Z}_q^*$, sends $c$ to Prover.
- **Pass 3 (Response):** Prover computes $s = (r + c \cdot x) \pmod q$, sends $s$ to Verifier.
- **Verification:** Verifier checks:
  $$g^s \stackrel{?}{\equiv} t \cdot Y^c \pmod p$$
  *Proof of Completeness:*
  $$g^s = g^{r + c \cdot x} = g^r \cdot (g^x)^c = t \cdot Y^c \pmod p$$

---

## Benchmark Evaluation Results

The numbers below are the full SOCOFing run (600 subjects, altered-easy). Training used 480 people. The test used the other 120, who were not in training.

| Measure | Training | Fresh test |
| :--- | :---: | :---: |
| Equal error rate | 1.717% | 1.539% |
| Wrong person accepted (FAR) | 0.216% | 0.177% |
| Right person rejected (FRR) | 4.878% | 4.466% |
| Separation score (AUC) | 0.997 | 0.996 |
| Real logins accepted | 13650 / 14350 | 3423 / 3583 |
| Fake logins that got in | 83 / 38400 | 17 / 9600 |

---

## 🛡️ Privacy & Zero Biometric Leakage

The database strictly conforms to biometric privacy standards (ISO/IEC 24745):
1. **Cancelable Biometrics:** If database credentials are compromised, a new random secret $C_{\text{new}}$ is chosen to produce new helper data $W_{\text{new}} = B \oplus \text{Codeword}(C_{\text{new}})$. The original biometric $B$ is not exposed.
2. **Non-Invertibility:** Helper data $W$ is mathematically one-time-padded by $\text{Codeword}(C)$, making it indistinguishable from uniform random noise without possessing the raw finger.
3. **Zero Private Key Storage:** Private key $x = C$ exists strictly in volatile RAM during the active session and is never persisted to disk.

---

## 📁 Repository Structure

```
UROP_FINALEv/
│
├── core/                           # Biometric processing & feature extraction
│   ├── __init__.py
│   ├── preprocessing.py            # Normalization, Gabor filtering, thinning
│   ├── minutiae.py                 # Crossing Number minutiae & core detection
│   └── template.py                 # 1024-bit binary template generation & alignment
│
├── crypto/                         # Cryptographic protocols & storage
│   ├── __init__.py
│   ├── ecc.py                      # Hadamard-128 Maximum Likelihood Code
│   ├── fuzzy_commitment.py         # Juels-Wattenberg Fuzzy Commitment scheme
│   ├── schnorr_zkp.py              # Schnorr 3-Pass Zero-Knowledge Proof protocol
│   └── database.py                 # SQLite interface storing ONLY (W, H, Y)
│
├── evaluation/                     # Benchmark & metrics evaluation
│   ├── __init__.py
│   ├── metrics.py                  # ROC, EER, FAR, FRR computation & plot generation
│   ├── evaluate_dataset.py         # Automated evaluation runner for Train & Test
│   └── plots/                      # Generated evaluation curve plots
│       ├── train_summary.png
│       └── test_summary.png
│
├── data/                           # Dataset partitions
│   ├── kaggle_socofing/            # Local SOCOFing sample (real and altered)
│   ├── secure_vault.db             # SQLite database storing (W, H, Y)
│   └── evaluation_results.json     # Persisted benchmark metrics
│
├── web/                            # Modern web dashboard interface
│   ├── __init__.py
│   ├── app.py                      # FastAPI REST application
│   ├── static/
│   │   ├── css/style.css           # Glassmorphism cyber-biometric styling
│   │   └── js/main.js              # Interactive UI controller & live pipeline
│   └── templates/
│       └── index.html              # Responsive single-page application
│
├── tests/                          # Automated test suite
│   ├── test_preprocessing.py       # Preprocessing unit tests
│   ├── test_minutiae.py            # Minutiae extraction unit tests
│   ├── test_crypto.py              # ECC, Fuzzy Commitment & ZKP tests
│   └── test_system.py              # Full end-to-end integration tests
│
├── run_demo.py                     # Interactive CLI demonstration
├── start_interface.py              # Launch script for the web interface
├── requirements.txt                # Python package dependencies
└── README.md                       # Comprehensive documentation
```

---

## 🚀 Quickstart Guide

### 1. Installation
Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run the Interactive Command-Line Demo
Experience the full enrollment, genuine authentication, impostor attack, and Schnorr ZKP from your terminal:
```bash
python run_demo.py
```

### 3. Launch the Modern Web Interface
Start the FastAPI server and launch the interactive browser dashboard:
```bash
python start_interface.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser.

### 4. Run the Automated Test Suite
Verify that all unit and integration tests pass:
```bash
pytest tests/ -v
```

### 5. Re-run Dataset Evaluation Benchmark
Recompute metrics and regenerate ROC plots across Train and Test datasets:
```bash
python evaluation/evaluate_dataset.py
```

---

## 📜 License
Developed for academic research and biometric security demonstration. Free for research and educational usage.

