import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

# =========================
# Parâmetros do sistema
# =========================
V_ll_rms = 380.0      # Tensão de linha RMS do trafo [V]
f = 60.0               # Frequência [Hz]
omega = 2*np.pi*f

R_linha = 0.4          # ohms/km
L_linha = 2e-3         # H/km

distancias = [10, 50]    # km até cada carga

# Parâmetros da carga
s_instalada = [3000, 3000]  # VA
fp = [0.8, 0.8]             # Fator de potência
v_nom = 380.0

# Construir impedâncias das cargas
Z_cargas = []
L_cargas = []
R_cargas = []
for i in range(len(s_instalada)):
    I_carga = s_instalada[i]/v_nom
    Z_mag = v_nom/I_carga
    R = Z_mag*fp[i]
    XL = Z_mag*np.sqrt(1-fp[i]**2)
    L = XL/(2*np.pi*f)
    Z_cargas.append(R + 1j*XL)
    R_cargas.append(R)
    L_cargas.append(L)

# print(Z_cargas)
# print(L_cargas)

n_cargas = len(distancias)
n_fases = 3  # trifásico

# =========================
# Montar matrizes M e K
# =========================
# Variáveis: i1a, i1b, i1c, i2a, i2b, i2c, ...
size = n_cargas * n_fases

M = np.zeros((size, size))
K = np.zeros((size, size))

# Preencher M e K
for k in range(n_cargas):
    for p in range(n_fases):
        idx = k*n_fases + p
        # Indutância total da linha + carga
        M[idx, idx] = L_linha*distancias[k] + L_cargas[k]
        # Resistência total
        K[idx, idx] = R_linha*distancias[k] + R_cargas[k]
        # Acoplamento: corrente da carga anterior influencia na tensão da carga atual
        if k > 0:
            for p2 in range(n_fases):
                idx_prev = (k-1)*n_fases + p2
                if p == p2:
                    K[idx, idx_prev] = -R_linha*(distancias[k]-distancias[k-1])

print(K)
# =========================
# Fonte do trafo
# =========================
def v_trafo(t):
    V_ln = V_ll_rms/np.sqrt(3)
    Va = V_ln * np.sqrt(2) * np.sin(omega*t)
    Vb = V_ln * np.sqrt(2) * np.sin(omega*t - 2*np.pi/3)
    Vc = V_ln * np.sqrt(2) * np.sin(omega*t + 2*np.pi/3)
    return np.array([Va, Vb, Vc])

# =========================
# EDO dx/dt = M^-1(f - K x)
# =========================
def dx_dt(t, x):
    f = np.zeros(size)
    f[0:3] = v_trafo(t)  # tensão do trafo alimenta a primeira carga
    dx = np.linalg.solve(M, f - K @ x)
    return dx

# =========================
# Resolver EDO
# =========================
t_span = (0, 0.05)  # 50 ms
t_eval = np.linspace(*t_span, 5000)
x0 = np.zeros(size)

sol = solve_ivp(dx_dt, t_span, x0, t_eval=t_eval)

# =========================
# Extrair correntes por carga
# =========================
currents = []
for k in range(n_cargas):
    currents.append(sol.y[k*n_fases:(k+1)*n_fases, :])

# =========================
# Calcular tensões nas cargas
# =========================
V_cargas = []
for k in range(n_cargas):
    V_k = np.zeros_like(currents[k])
    for p in range(n_fases):
        # V = V_trafo - queda de tensão da linha até aqui - queda de carga
        idx = k*n_fases + p
        i = sol.y[idx, :]
        R_line = R_linha*distancias[k]
        L_line = L_linha*distancias[k]
        V_k[p,:] = v_trafo(t_eval)[p] - R_line*i - L_line*np.gradient(i, t_eval)
    V_cargas.append(V_k)

# =========================
# Corrente total no trafo
# =========================
I_trafo = np.zeros((3, len(t_eval)))  # 3 fases
for k in range(n_cargas):
    I_trafo += currents[k]  # currents[k] tem shape (3, len(t_eval))

# =========================
# Plotar resultados
# =========================
fig, axs = plt.subplots(n_cargas+1, 2, figsize=(14, 10), sharex=True)

# Cargas
for k in range(n_cargas):
    axs[k,0].plot(t_eval*1000, V_cargas[k][0], label='Va')
    axs[k,0].plot(t_eval*1000, V_cargas[k][1], label='Vb')
    axs[k,0].plot(t_eval*1000, V_cargas[k][2], label='Vc')
    axs[k,0].set_ylabel(f"V Carga {k+1} [V]")
    axs[k,0].grid(True)
    axs[k,0].legend()
    
    axs[k,1].plot(t_eval*1000, currents[k][0], label='Ia')
    axs[k,1].plot(t_eval*1000, currents[k][1], label='Ib')
    axs[k,1].plot(t_eval*1000, currents[k][2], label='Ic')
    axs[k,1].set_ylabel(f"I Carga {k+1} [A]")
    axs[k,1].grid(True)
    axs[k,1].legend()

# Trafo
axs[-1,0].plot(t_eval*1000, v_trafo(t_eval)[0], label='Va')
axs[-1,0].plot(t_eval*1000, v_trafo(t_eval)[1], label='Vb')
axs[-1,0].plot(t_eval*1000, v_trafo(t_eval)[2], label='Vc')
axs[-1,0].set_ylabel("V Trafo [V]")
axs[-1,0].grid(True)
axs[-1,0].legend()

axs[-1,1].plot(t_eval*1000, I_trafo[0], label='Ia')
axs[-1,1].plot(t_eval*1000, I_trafo[1], label='Ib')
axs[-1,1].plot(t_eval*1000, I_trafo[2], label='Ic')
axs[-1,1].set_ylabel("I Trafo [A]")
axs[-1,1].grid(True)
axs[-1,1].legend()
axs[-1,1].set_xlabel("Tempo [ms]")
axs[-1,0].set_xlabel("Tempo [ms]")

plt.tight_layout()
plt.show()
