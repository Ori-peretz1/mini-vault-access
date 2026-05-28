import { useMemo, useState } from "react";

const API_BASE = "http://127.0.0.1:8000";

const roles = ["admin", "operator", "auditor"];
const safeTypes = ["linux_accounts", "production", "database"];
const permissions = ["read", "use", "manage"];
const platforms = ["linux_ssh", "database", "windows_rdp", "ci_cd"];

const styles = {
  page: {
    minHeight: "100vh",
    background:
      "radial-gradient(circle at top left, rgba(34, 211, 238, 0.18), transparent 32%), #020617",
    color: "#e5e7eb",
    fontFamily: "Inter, Segoe UI, Arial, sans-serif",
    padding: "32px",
  },
  shell: {
    maxWidth: "1200px",
    margin: "0 auto",
  },
  header: {
    border: "1px solid #1e293b",
    background: "rgba(15, 23, 42, 0.85)",
    borderRadius: "24px",
    padding: "28px",
    marginBottom: "24px",
    boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
  },
  title: {
    fontSize: "42px",
    margin: "0 0 8px",
    color: "white",
  },
  subtitle: {
    margin: 0,
    color: "#94a3b8",
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
    gap: "18px",
  },
  card: {
    border: "1px solid #1e293b",
    background: "rgba(15, 23, 42, 0.9)",
    borderRadius: "22px",
    padding: "22px",
  },
  fullCard: {
    gridColumn: "1 / -1",
    border: "1px solid #1e293b",
    background: "rgba(15, 23, 42, 0.9)",
    borderRadius: "22px",
    padding: "22px",
  },
  sectionTitle: {
    fontSize: "20px",
    margin: "0 0 6px",
    color: "white",
  },
  sectionText: {
    color: "#94a3b8",
    margin: "0 0 16px",
    fontSize: "14px",
  },
  row: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
    gap: "12px",
    marginBottom: "12px",
  },
  label: {
    display: "block",
    color: "#94a3b8",
    fontSize: "12px",
    marginBottom: "6px",
  },
  input: {
    width: "100%",
    boxSizing: "border-box",
    borderRadius: "12px",
    border: "1px solid #334155",
    background: "#020617",
    color: "#e5e7eb",
    padding: "10px 12px",
    outline: "none",
  },
  button: {
    border: "0",
    borderRadius: "12px",
    padding: "10px 14px",
    background: "#06b6d4",
    color: "#082f49",
    fontWeight: 700,
    cursor: "pointer",
    marginRight: "8px",
    marginTop: "8px",
  },
  secondaryButton: {
    border: "1px solid #334155",
    borderRadius: "12px",
    padding: "10px 14px",
    background: "#0f172a",
    color: "#e5e7eb",
    fontWeight: 700,
    cursor: "pointer",
    marginRight: "8px",
    marginTop: "8px",
  },
  statusSuccess: {
    border: "1px solid rgba(16,185,129,0.4)",
    background: "rgba(16,185,129,0.12)",
    color: "#a7f3d0",
    borderRadius: "16px",
    padding: "12px 16px",
    marginBottom: "18px",
  },
  statusError: {
    border: "1px solid rgba(239,68,68,0.4)",
    background: "rgba(239,68,68,0.12)",
    color: "#fecaca",
    borderRadius: "16px",
    padding: "12px 16px",
    marginBottom: "18px",
  },
  item: {
    border: "1px solid #1e293b",
    background: "#020617",
    borderRadius: "16px",
    padding: "14px",
    marginTop: "10px",
  },
  code: {
    fontFamily: "Consolas, monospace",
    color: "#67e8f9",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    fontSize: "14px",
  },
  th: {
    textAlign: "left",
    color: "#94a3b8",
    borderBottom: "1px solid #334155",
    padding: "10px",
  },
  td: {
    borderBottom: "1px solid #1e293b",
    padding: "10px",
    verticalAlign: "top",
  },
};

function Field({ label, value, onChange, type = "text", options }) {
  return (
    <div>
      <label style={styles.label}>{label}</label>
      {options ? (
        <select style={styles.input} value={value} onChange={(event) => onChange(event.target.value)}>
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : (
        <input
          style={styles.input}
          value={value}
          type={type}
          onChange={(event) => onChange(event.target.value)}
        />
      )}
    </div>
  );
}

export default function App() {
  const [status, setStatus] = useState({ type: "success", message: "Frontend ready" });
  const [token, setToken] = useState(localStorage.getItem("miniVaultToken") || "");
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [safes, setSafes] = useState([]);
  const [selectedSafeId, setSelectedSafeId] = useState("s_1");
  const [members, setMembers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [secret, setSecret] = useState(null);

  const [registerForm, setRegisterForm] = useState({ username: "Ori", role: "admin", password: "123456" });
  const [loginForm, setLoginForm] = useState({ username: "Ori", password: "123456" });
  const [safeForm, setSafeForm] = useState({
    name: "Production Linux Servers",
    safe_type: "linux_accounts",
    description: "Privileged Linux accounts",
  });
  const [memberForm, setMemberForm] = useState({ user_id: "u_2", permission_level: "use" });
  const [accountForm, setAccountForm] = useState({
    username: "root",
    target: "prod-linux-01",
    platform: "linux_ssh",
    secret_value: "fake-root-secret",
  });

  const authHeaders = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);

  function showSuccess(message) {
    setStatus({ type: "success", message });
  }

  function showError(message) {
    setStatus({ type: "error", message });
  }

  function clearAuthState() {
    localStorage.removeItem("miniVaultToken");
    setToken("");
    setCurrentUser(null);
    setSafes([]);
    setMembers([]);
    setAccounts([]);
    setAuditLogs([]);
    setSecret(null);
  }

  function handleUnauthorized(path, message) {
    if (path !== "/login") {
      clearAuthState();
      throw new Error("Session expired or revoked. Please log in again.");
    }

    throw new Error(message);
  }

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
    });

    const text = await response.text();
    const data = text ? JSON.parse(text) : null;

    if (!response.ok) {
      const message = data?.detail || `Request failed with status ${response.status}`;

      if (response.status === 401) {
        handleUnauthorized(path, message);
      }

      throw new Error(message);
    }

    return data;
  }

  async function safeAction(action, message) {
    try {
      const data = await action();
      showSuccess(message);
      return data;
    } catch (error) {
      showError(error.message);
      return null;
    }
  }

  async function createUser() {
    const data = await safeAction(
      () => request("/users", { method: "POST", body: JSON.stringify(registerForm) }),
      "User created"
    );
    if (data) await loadUsers();
  }

  async function loadUsers() {
    const data = await safeAction(() => request("/users"), "Users loaded");
    if (data) setUsers(data);
  }

  async function login() {
    const data = await safeAction(
      () => request("/login", { method: "POST", body: JSON.stringify(loginForm) }),
      "Login succeeded"
    );
    if (data?.access_token) {
      const newToken = data.access_token;
      setToken(newToken);
      localStorage.setItem("miniVaultToken", newToken);
      setCurrentUser(null);
      setSafes([]);
      setMembers([]);
      setAccounts([]);
      setAuditLogs([]);
      setSecret(null);

      const me = await safeAction(
        () => request("/me", { headers: { Authorization: `Bearer ${newToken}` } }),
        "Login succeeded and current user loaded"
      );

      if (me) setCurrentUser(me);
    }
  }

  async function loadMe() {
    const data = await safeAction(() => request("/me", { headers: authHeaders }), "Current user loaded");
    if (data) setCurrentUser(data);
  }

  async function logout() {
    if (!token) {
      clearAuthState();
      showSuccess("Logged out locally");
      return;
    }

    const data = await safeAction(
      () => request("/logout", { method: "POST", headers: authHeaders }),
      "Logged out successfully"
    );

    if (data) {
      clearAuthState();
      showSuccess(data.logout_msg || "Logged out successfully");
    }
  }

  async function createSafe() {
    const data = await safeAction(
      () => request("/safes", { method: "POST", headers: authHeaders, body: JSON.stringify(safeForm) }),
      "Safe created"
    );
    if (data) await loadSafes();
  }

  async function loadSafes() {
    const data = await safeAction(() => request("/safes", { headers: authHeaders }), "Safes loaded");
    if (data) {
      setSafes(data);
      if (data[0]?.id) setSelectedSafeId(data[0].id);
    }
  }

  async function addMember() {
    const data = await safeAction(
      () =>
        request(`/safes/${selectedSafeId}/members`, {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify(memberForm),
        }),
      "Member added"
    );
    if (data) await loadMembers();
  }

  async function loadMembers() {
    const data = await safeAction(
      () => request(`/safes/${selectedSafeId}/members`, { headers: authHeaders }),
      "Members loaded"
    );
    if (data) setMembers(data);
  }

  async function createAccount() {
    const data = await safeAction(
      () =>
        request(`/safes/${selectedSafeId}/accounts`, {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify(accountForm),
        }),
      "Account created"
    );
    if (data) await loadAccounts();
  }

  async function loadAccounts() {
    const data = await safeAction(
      () => request(`/safes/${selectedSafeId}/accounts`, { headers: authHeaders }),
      "Accounts loaded"
    );
    if (data) setAccounts(data);
  }

  async function retrieveSecret(accountId) {
    const data = await safeAction(
      () =>
        request(`/safes/${selectedSafeId}/accounts/${accountId}/retrieve`, {
          method: "POST",
          headers: authHeaders,
        }),
      "Secret retrieved"
    );
    if (data) setSecret(data);
  }

  async function loadAuditLogs() {
    const data = await safeAction(() => request("/audit-logs", { headers: authHeaders }), "Audit logs loaded");
    if (data) setAuditLogs(data);
  }

  return (
    <div style={styles.page}>
      <div style={styles.shell}>
        <header style={styles.header}>
          <h1 style={styles.title}>Mini Vault Access Project</h1>
          <p style={styles.subtitle}>Fullstack frontend for your FastAPI + SQLite privileged access lab.</p>
          <p style={styles.subtitle}>Backend: <span style={styles.code}>{API_BASE}</span></p>
          <p style={styles.subtitle}>Token: <span style={styles.code}>{token || "No token yet"}</span></p>
          <p style={styles.subtitle}>Current user: <span style={styles.code}>{currentUser ? `${currentUser.id} | ${currentUser.username} | ${currentUser.role}` : "Not loaded"}</span></p>
        </header>

        <div style={status.type === "error" ? styles.statusError : styles.statusSuccess}>{status.message}</div>

        <div style={styles.grid}>
          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>1. Register user</h2>
            <p style={styles.sectionText}>Create admin, operator, or auditor users.</p>
            <div style={styles.row}>
              <Field label="Username" value={registerForm.username} onChange={(v) => setRegisterForm({ ...registerForm, username: v })} />
              <Field label="Role" value={registerForm.role} onChange={(v) => setRegisterForm({ ...registerForm, role: v })} options={roles} />
              <Field label="Password" type="password" value={registerForm.password} onChange={(v) => setRegisterForm({ ...registerForm, password: v })} />
            </div>
            <button style={styles.button} onClick={createUser}>Create user</button>
            <button style={styles.secondaryButton} onClick={loadUsers}>Load users</button>
            {users.map((user) => (
              <div key={user.id} style={styles.item}><span style={styles.code}>{user.id}</span> | {user.username} | {user.role}</div>
            ))}
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>2. Login</h2>
            <p style={styles.sectionText}>Login returns a bearer token. Load /me identifies the current user.</p>
            <div style={styles.row}>
              <Field label="Username" value={loginForm.username} onChange={(v) => setLoginForm({ ...loginForm, username: v })} />
              <Field label="Password" type="password" value={loginForm.password} onChange={(v) => setLoginForm({ ...loginForm, password: v })} />
            </div>
            <button style={styles.button} onClick={login}>Login</button>
            <button style={styles.secondaryButton} onClick={loadMe}>Load /me</button>
            <button style={styles.secondaryButton} onClick={logout}>Logout</button>
          </section>

          <section style={styles.fullCard}>
            <h2 style={styles.sectionTitle}>3. Safes</h2>
            <p style={styles.sectionText}>Create safe and load safes using bearer token authentication.</p>
            <div style={styles.row}>
              <Field label="Name" value={safeForm.name} onChange={(v) => setSafeForm({ ...safeForm, name: v })} />
              <Field label="Safe type" value={safeForm.safe_type} onChange={(v) => setSafeForm({ ...safeForm, safe_type: v })} options={safeTypes} />
              <Field label="Description" value={safeForm.description} onChange={(v) => setSafeForm({ ...safeForm, description: v })} />
            </div>
            <button style={styles.button} onClick={createSafe}>Create safe</button>
            <button style={styles.secondaryButton} onClick={loadSafes}>Load safes</button>
            <Field label="Selected safe id" value={selectedSafeId} onChange={setSelectedSafeId} />
            {safes.map((safe) => (
              <div key={safe.id} style={styles.item} onClick={() => setSelectedSafeId(safe.id)}>
                <strong>{safe.name}</strong> | <span style={styles.code}>{safe.id}</span> | {safe.safe_type}<br />
                <span style={{ color: "#94a3b8" }}>{safe.description}</span>
              </div>
            ))}
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>4. Members</h2>
            <p style={styles.sectionText}>Uses bearer token authentication.</p>
            <div style={styles.row}>
              <Field label="User id" value={memberForm.user_id} onChange={(v) => setMemberForm({ ...memberForm, user_id: v })} />
              <Field label="Permission" value={memberForm.permission_level} onChange={(v) => setMemberForm({ ...memberForm, permission_level: v })} options={permissions} />
            </div>
            <button style={styles.button} onClick={addMember}>Add member</button>
            <button style={styles.secondaryButton} onClick={loadMembers}>Load members</button>
            {members.map((member) => (
              <div key={`${member.safe_id}-${member.user_id}`} style={styles.item}>
                <span style={styles.code}>{member.user_id}</span> | {member.permission_level} | {member.safe_id}
              </div>
            ))}
          </section>

          <section style={styles.card}>
            <h2 style={styles.sectionTitle}>5. Accounts and secrets</h2>
            <p style={styles.sectionText}>Create account metadata, then retrieve the secret.</p>
            <div style={styles.row}>
              <Field label="Username" value={accountForm.username} onChange={(v) => setAccountForm({ ...accountForm, username: v })} />
              <Field label="Target" value={accountForm.target} onChange={(v) => setAccountForm({ ...accountForm, target: v })} />
              <Field label="Platform" value={accountForm.platform} onChange={(v) => setAccountForm({ ...accountForm, platform: v })} options={platforms} />
              <Field label="Secret value" value={accountForm.secret_value} onChange={(v) => setAccountForm({ ...accountForm, secret_value: v })} />
            </div>
            <button style={styles.button} onClick={createAccount}>Create account</button>
            <button style={styles.secondaryButton} onClick={loadAccounts}>Load accounts</button>
            {accounts.map((account) => (
              <div key={account.id} style={styles.item}>
                <strong>{account.username}</strong> | <span style={styles.code}>{account.id}</span> | {account.target} | {account.platform}
                <br />
                <button style={styles.secondaryButton} onClick={() => retrieveSecret(account.id)}>Retrieve secret</button>
              </div>
            ))}
            {secret && (
              <div style={styles.statusSuccess}>
                Secret for <span style={styles.code}>{secret.account_id}</span>: <strong>{secret.secret_value}</strong>
              </div>
            )}
          </section>

          <section style={styles.fullCard}>
            <h2 style={styles.sectionTitle}>6. Audit logs</h2>
            <p style={styles.sectionText}>Admin-only audit log view.</p>
            <button style={styles.button} onClick={loadAuditLogs}>Load audit logs</button>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>ID</th>
                  <th style={styles.th}>Actor</th>
                  <th style={styles.th}>Action</th>
                  <th style={styles.th}>Success</th>
                  <th style={styles.th}>Message</th>
                  <th style={styles.th}>Time</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td style={styles.td}>{log.id}</td>
                    <td style={styles.td}>{log.actor_user_id}</td>
                    <td style={styles.td}>{log.action}</td>
                    <td style={styles.td}>{String(log.success)}</td>
                    <td style={styles.td}>{log.message}</td>
                    <td style={styles.td}>{log.time}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      </div>
    </div>
  );
}
