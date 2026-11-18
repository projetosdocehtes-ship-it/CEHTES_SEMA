import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# -------------------------
# Parâmetros do sistema
# -------------------------
V_ll_rms = 380.0
f = 60.0
omega = 2*np.pi*f

R_linha = 0.04       # ohm/km
L_linha = 2e-5      # H/km

d1 = 10.0            # km (trafo -> carga 1)
d2 = 50.0            # km (carga 1 -> carga 2: será d2-d1)

# Cargas: potência aparente trifásica e fp (para obter R,L por fase)
S1 = 3000.0; pf1 = 0.8
S2 = 3000.0; pf2 = 0.8
V_ln_rms = V_ll_rms/np.sqrt(3)

def RL_from_S_pf(S, pf):
    I_rms_line = S/(np.sqrt(3)*V_ll_rms)  # corrente de linha (rms)
    Zmag = V_ln_rms / I_rms_line          # impedância por fase (módulo)
    R = Zmag * pf
    XL = Zmag*np.sqrt(max(0.0,1.0-pf**2))
    L = XL/omega
    if S == 0:
        return 1e15, 1e15
    
    return R, L

R_L1, L_L1 = RL_from_S_pf(S1, pf1)
R_L2, L_L2 = RL_from_S_pf(S2, pf2)

# Linha por trechos
R_s1 = R_linha * d1
L_s1 = L_linha * d1
R_s2 = R_linha * (d2 - d1)
L_s2 = L_linha * (d2 - d1)

# -------------------------
# Fonte do trafo (por fase)
# -------------------------
def v_trafo_phase(t):
    Vpk = V_ln_rms*np.sqrt(2)
    Va = Vpk*np.sin(omega*t)
    Vb = Vpk*np.sin(omega*t - 2*np.pi/3)
    Vc = Vpk*np.sin(omega*t + 2*np.pi/3)
    return np.array([Va, Vb, Vc])  # shape (3,)

# -------------------------
# Blocos por fase (3x3)
# M_p * xdot + K_p * x = f_p(t)
# x = [i_s1, i_L1, i_s2]^T
# -------------------------
def phase_blocks(Rs1,Ls1, RL1,LL1, Rs2,Ls2, RL2,LL2):
    M = np.array([
        [Ls1,      LL1,          0.0],
        [0.0,     -LL1,    Ls2 + LL2],
        [1.0,     -1.0,        -1.0]
    ], dtype=float)

    K = np.array([
        [Rs1,      RL1,          0.0],
        [0.0,     -RL1,    Rs2 + RL2],
        [0.0,      0.0,         0.0]
    ], dtype=float)
    return M, K

M_phase, K_phase = phase_blocks(R_s1,L_s1, R_L1,L_L1, R_s2,L_s2, R_L2,L_L2)

# Empilhar 3 fases em bloco-diagonal (9x9)
M = np.zeros((9,9))
K = np.zeros((9,9))
for b in range(3):
    i0 = 3*b
    M[i0:i0+3, i0:i0+3] = M_phase
    K[i0:i0+3, i0:i0+3] = K_phase
# print(M)
print(K)
# -------------------------
# EDO: M xdot + K x = f(t)  -> xdot = M^{-1}(f - Kx)
# x = [i_s1^a, i_L1^a, i_s2^a,  i_s1^b, i_L1^b, i_s2^b,  i_s1^c, i_L1^c, i_s2^c]^T
# -------------------------
def f_vector(t):
    f = np.zeros(9)
    vt = v_trafo_phase(t)  # [Va,Vb,Vc]
    f[0] = vt[0]  # fase a, eq. 1
    f[3] = vt[1]  # fase b, eq. 1
    f[6] = vt[2]  # fase c, eq. 1
    return f

Minv = np.linalg.inv(M)

def rhs(t, x):
    return Minv @ (f_vector(t) - K @ x)

# -------------------------
# Integração
# -------------------------
t_span = (0.0, 0.05)  # 50 ms
t_eval = np.linspace(*t_span, 5000)
x0 = np.zeros(9)
sol = solve_ivp(rhs, t_span, x0, t_eval=t_eval, rtol=1e-7, atol=1e-9)

# -------------------------
# Pós-processamento
# -------------------------
# Reorganizar por fase
i_s1 = sol.y[0:9:3, :]  # shape (3 fases, Nt)
i_L1 = sol.y[1:9:3, :]
i_s2 = sol.y[2:9:3, :]  # = i_L2

# Derivadas para tensões nas cargas
dt = t_eval[1]-t_eval[0]
di_L1_dt = np.gradient(i_L1, dt, axis=1)
di_s2_dt  = np.gradient(i_s2,  dt, axis=1)

# Tensões de fase nos PCCs:
# v1 = R_L1*i_L1 + L_L1*di_L1/dt
# v2 = R_L2*i_s2 + L_L2*di_s2/dt
v1 = R_L1*i_L1 + L_L1*di_L1_dt
v2 = R_L2*i_s2 + L_L2*di_s2_dt

# Corrente do trafo (por fase) = corrente no trecho 1
I_traf = i_s1

# -------------------------
# Plots
# -------------------------
fig, axs = plt.subplots(3, 2, figsize=(13, 9), sharex=True)

# Carga 1: tensões e correntes
axs[0,0].plot(t_eval*1000, v1[0], label='Va1')
axs[0,0].plot(t_eval*1000, v1[1], label='Vb1')
axs[0,0].plot(t_eval*1000, v1[2], label='Vc1')
axs[0,0].set_title('Tensão no PCC da Carga 1')
axs[0,0].set_ylabel('V [V]'); axs[0,0].grid(True); axs[0,0].legend()

axs[0,1].plot(t_eval*1000, i_L1[0], label='Ia1')
axs[0,1].plot(t_eval*1000, i_L1[1], label='Ib1')
axs[0,1].plot(t_eval*1000, i_L1[2], label='Ic1')
axs[0,1].set_title('Corrente da Carga 1')
axs[0,1].set_ylabel('I [A]'); axs[0,1].grid(True); axs[0,1].legend()

# Carga 2: tensões e correntes
axs[1,0].plot(t_eval*1000, v2[0], label='Va2')
axs[1,0].plot(t_eval*1000, v2[1], label='Vb2')
axs[1,0].plot(t_eval*1000, v2[2], label='Vc2')
axs[1,0].set_title('Tensão no PCC da Carga 2')
axs[1,0].set_ylabel('V [V]'); axs[1,0].grid(True); axs[1,0].legend()

axs[1,1].plot(t_eval*1000, i_s2[0], label='Ia2 (i_L2)')
axs[1,1].plot(t_eval*1000, i_s2[1], label='Ib2 (i_L2)')
axs[1,1].plot(t_eval*1000, i_s2[2], label='Ic2 (i_L2)')
axs[1,1].set_title('Corrente da Carga 2')
axs[1,1].set_ylabel('I [A]'); axs[1,1].grid(True); axs[1,1].legend()

# Trafo: tensão e corrente
vt = v_trafo_phase(t_eval)  # shape (3, Nt)
axs[2,0].plot(t_eval*1000, vt[0], label='VaT')
axs[2,0].plot(t_eval*1000, vt[1], label='VbT')
axs[2,0].plot(t_eval*1000, vt[2], label='VcT')
axs[2,0].set_title('Tensão do Trafo (fase)')
axs[2,0].set_ylabel('V [V]'); axs[2,0].grid(True); axs[2,0].legend()

axs[2,1].plot(t_eval*1000, I_traf[0], label='IaT')
axs[2,1].plot(t_eval*1000, I_traf[1], label='IbT')
axs[2,1].plot(t_eval*1000, I_traf[2], label='IcT')
axs[2,1].set_title('Corrente do Trafo (fase) = i_s1')
axs[2,1].set_ylabel('I [A]'); axs[2,1].grid(True); axs[2,1].legend()

for ax in axs[-1,:]:
    ax.set_xlabel('Tempo [ms]')

plt.tight_layout()
plt.show()
