import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

fig, ax = plt.subplots(figsize=(16, 10.5), dpi=300)
ax.set_xlim(0, 16)
ax.set_ylim(0, 10.5)
ax.axis('off')

# Background canvas styling
ax.add_patch(patches.Rectangle((0, 0), 16, 10.5, facecolor='#FAFAFA', edgecolor='none'))

def draw_box(x, y, w, h, title, subtitle, bg_col, edge_col, title_col='#1A252C', sub_col='#34495E', title_size=11, sub_size=9, lw=1.5, radius=0.2):
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0.08,rounding_size={radius}',
                                facecolor=bg_col, edgecolor=edge_col, linewidth=lw, zorder=2)
    ax.add_patch(box)
    if subtitle:
        ax.text(x + w/2, y + h*0.62, title, ha='center', va='center', fontsize=title_size, fontweight='bold', color=title_col, zorder=3)
        ax.text(x + w/2, y + h*0.30, subtitle, ha='center', va='center', fontsize=sub_size, color=sub_col, zorder=3)
    else:
        ax.text(x + w/2, y + h/2, title, ha='center', va='center', fontsize=title_size, fontweight='bold', color=title_col, zorder=3)

def draw_arrow(x1, y1, x2, y2, label='', color='#2C3E50', lw=1.8, label_pos='top', label_size=8.5, label_col='#2C3E50'):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->,head_width=0.35,head_length=0.45', color=color, lw=lw), zorder=4)
    if label:
        mx, my = (x1 + x2)/2, (y1 + y2)/2
        dy = 0.18 if label_pos == 'top' else -0.22
        ax.text(mx, my + dy, label, ha='center', va='center', fontsize=label_size, fontweight='bold', color=label_col, zorder=5,
                bbox=dict(boxstyle='round,pad=0.15', facecolor='#FFFFFF', edgecolor='none', alpha=0.9))

# Main Containers for Phase 1 (Enrollment) and Phase 2 (Authentication)
box_p1 = patches.FancyBboxPatch((0.5, 5.4), 15.0, 4.6, boxstyle='round,pad=0.15,rounding_size=0.3',
                               facecolor='#F0F4F8', edgecolor='#CBD5E1', linewidth=1.5, zorder=1)
ax.add_patch(box_p1)
ax.text(0.8, 9.65, 'PHASE 1: IDENTITY ENROLLMENT & VAULT REGISTRATION (LOGIN SETUP)', 
        fontsize=12, fontweight='bold', color='#1E293B', ha='left', va='center', zorder=3)

box_p2 = patches.FancyBboxPatch((0.5, 0.4), 15.0, 4.7, boxstyle='round,pad=0.15,rounding_size=0.3',
                               facecolor='#F0FDF4', edgecolor='#BBF7D0', linewidth=1.5, zorder=1)
ax.add_patch(box_p2)
ax.text(0.8, 4.75, 'PHASE 2: ZERO-KNOWLEDGE AUTHENTICATION & SECURE LOGIN VERIFICATION', 
        fontsize=12, fontweight='bold', color='#065F46', ha='left', va='center', zorder=3)

# ----------------- PHASE 1: ENROLLMENT BOXES -----------------
draw_box(0.8, 6.0, 2.3, 3.2, '1. Biometric Capture', 'Raw Fingerprint Scan\n500x400 Grayscale\n(Unaltered Enrollment)', '#FFFFFF', '#3B82F6', title_col='#1D4ED8')
draw_arrow(3.1, 7.6, 3.7, 7.6, 'Raw Image')

draw_box(3.7, 6.0, 2.7, 3.2, '2. Feature Extraction', '• Core Localization (xc, yc)\n• Circular Gabor Bank (8 dirs)\n• 128 Sectors (AAD energy)\n➜ 1024-bit FingerCode b', '#EFF6FF', '#2563EB', title_col='#1E40AF')
draw_arrow(6.4, 7.6, 7.0, 7.6, 'b in {0,1}^1024')

draw_box(7.0, 7.5, 3.5, 1.7, '3. Ephemeral Key Gen', 'Random Secret s in {0,1}^64\nHadamard-128 Encoding:\nC(s) = [c1...c8] in {0,1}^1024', '#FDF4FF', '#A855F7', title_col='#6B21A8')

draw_box(7.0, 5.7, 3.5, 1.5, '4. Fuzzy Commitment', 'W = b XOR C(s) (Helper Data)\nH(s) = SHA-256(s)\nY = g^s mod p (MODP-2048)', '#FAF5FF', '#9333EA', title_col='#581C87')
draw_arrow(8.75, 7.5, 8.75, 7.2)

draw_arrow(10.5, 6.45, 11.2, 7.2, 'Store Public Tuple\n{W, H(s), Y, xc, yc}')

draw_box(11.2, 6.0, 3.9, 3.2, '5. Secure Vault Database', 'Zero-Leakage SQLite DB:\n• username: VARCHAR\n• helper_data_w: BLOB\n• commitment_h: SHA-256\n• public_key_y: 2048-bit Key\n• center_x, center_y: INT\n[RAW TEMPLATE DISCARDED]', '#1E293B', '#0F172A', title_col='#F8FAFC', sub_col='#94A3B8')

# ----------------- PHASE 2: AUTHENTICATION BOXES -----------------
draw_box(0.8, 1.0, 2.3, 3.3, '1. Query Capture', 'Probe Fingerprint Scan\n(May be Rotated, Z-Cut,\nor Obliterated Query)', '#FFFFFF', '#10B981', title_col='#047857')
draw_arrow(3.1, 2.65, 3.7, 2.65, 'Probe Image')

draw_box(3.7, 1.0, 2.7, 3.3, '2. Query Extraction', '• Core Alignment (xc, yc)\n• Gabor Filterbank (8 dirs)\n• Sector Normalization\n➜ Query Vector b*', '#F0FDF4', '#059669', title_col='#065F46')
draw_arrow(6.4, 2.65, 7.0, 2.65, 'b* in {0,1}^1024')

draw_box(7.0, 1.0, 3.5, 3.3, '3. Fuzzy Recovery & Decoding', 'Retrieve Helper Data W from DB\nC* = W XOR b* = C(s) XOR (b XOR b*)\nHadamard-128 Maximum Likelihood:\nt = 31 bit error correction / block\n➜ Reconstruct Secret s*\nLocal Integrity: SHA-256(s*) == H(s)', '#ECFDF5', '#047857', title_col='#064E3B')

# Arrow from DB to Fuzzy Recovery
draw_arrow(11.2, 6.2, 10.5, 3.3, 'Fetch W, H(s), Y', color='#D97706', lw=1.6, label_col='#B45309')

# Schnorr ZKP 3-Pass Interactive Authentication Box
draw_box(10.9, 1.0, 4.2, 3.3, '4. 3-Pass Schnorr ZKP Authentication Protocol', '', '#FFFBEB', '#D97706', title_col='#92400E')

# ZKP 3 passes inside
ax.text(13.0, 3.85, 'PROVER (Client)  <==== 3-Pass ZKP ====>  VERIFIER (Server)', fontsize=8.5, fontweight='bold', color='#78350F', ha='center', va='center', zorder=3)
ax.text(13.0, 3.35, 'Pass 1 (Commitment): Prover picks nonce r, sends t = g^r mod p ──>', fontsize=7.8, color='#1E293B', ha='center', va='center', zorder=3)
ax.text(13.0, 2.85, '<── Pass 2 (Challenge): Verifier sends 160-bit challenge scalar c', fontsize=7.8, color='#1E293B', ha='center', va='center', zorder=3)
ax.text(13.0, 2.35, 'Pass 3 (Response): Prover computes z = (r + c · s*) mod q ──>', fontsize=7.8, color='#1E293B', ha='center', va='center', zorder=3)
ax.text(13.0, 1.75, 'Verification Equation: g^z == t · Y^c (mod p)\n' + r'g^{r + c·s} = g^r · (g^s)^c  [MATCH -> ACCESS GRANTED]', 
        fontsize=8.2, fontweight='bold', color='#047857', ha='center', va='center', zorder=3,
        bbox=dict(boxstyle='round,pad=0.2', facecolor='#DCFCE7', edgecolor='#86EFAC'))

draw_arrow(10.5, 2.4, 10.9, 2.4, 'Witness s*')

plt.tight_layout()
os.makedirs('conference_paper/figures', exist_ok=True)
out_path = 'conference_paper/figures/diag.png'
plt.savefig(out_path, dpi=300)
# Also copy to fig1_architecture.png
import shutil
shutil.copyfile(out_path, 'conference_paper/figures/fig1_architecture.png')
print('Successfully generated clean architecture diagram at:', out_path)
