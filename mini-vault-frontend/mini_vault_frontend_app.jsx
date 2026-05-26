import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  Eye,
  KeyRound,
  Lock,
  LogIn,
  Plus,
  RefreshCw,
  Shield,
  UserPlus,
  Users,
  Vault,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const API_BASE = "http://127.0.0.1:8000";

const safeTypes = ["linux_accounts", "production", "database"];
const roles = ["admin", "operator", "auditor"];
const permissionLevels = ["read", "use", "manage"];
const platforms = ["linux_ssh", "database", "windows_rdp", "ci_cd"];

function Field({ label, value, onChange, type = "text", placeholder, options }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-slate-400">{label}</span>
      {options ? (
        <select
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-cyan-400"
        >
          {options.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      ) : (
        <input
          value={value}
          type={type}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition placeholder:text-slate-600 focus:border-cyan-400"
        />
      )}
    </label>
  );
}

function StatusBox({ status }) {
  if (!status.message) return null;

  const Icon = status.type === "error" ? AlertTriangle : CheckCircle2;

  return (
    <div
      className={`flex items-start gap-2 rounded-2xl border px-4 py-3 text-sm ${
        status.type === "error"
          ? "border-red-500/40 bg-red-500/10 text-red-200"
          : "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
      }`}
    >
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <span>{status.message}</span>
    </div>
  );
}

function SectionTitle({ icon: Icon, title, subtitle }) {
  return (
    <div className="mb-4 flex items-center gap-3">
      <div className="rounded-2xl bg-cyan-400/10 p-2 text-cyan-300">
        <Icon className="h-5 w-5" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        <p className="text-sm text-slate-400">{subtitle}</p>
      </div>
    </div>
  );
}

export default function App() {
  const [status, setStatus] = useState({ type: "success", message: "" });
  const [token, setToken] = useState(localStorage.getItem("miniVaultToken") || "");
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [safes, setSafes] = useState([]);
  const [selectedSafeId, setSelectedSafeId] = useState("s_1");
  const [safeMembers, setSafeMembers] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [retrievedSecret, setRetrievedSecret] = useState(null);
  const [loading, setLoading] = useState(false);

  const [registerForm, setRegisterForm] = useState({
    username: "Ori",
    role: "admin",
    password: "123456",
  });

  const [loginForm, setLoginForm] = useState({
    username: "Ori",
    password: "123456",
  });

  const [safeForm, setSafeForm] = useState({
    name: "Production Linux Servers",
    safe_type: "linux_accounts",
    description: "Privileged Linux accounts",
  });

  const [memberForm, setMemberForm] = useState({
    user_id: "u_2",
    permission_level: "use",
  });

  const [accountForm, setAccountForm] = useState({
    username: "root",
    target: "prod-linux-01",
    platform: "linux_ssh",
    secret_value: "fake-root-secret",
  });

  const authHeaders = useMemo(() => {
    if (!token) return {};
    return { Authorization: `Bearer ${token}` };
  }, [token]);

  function showSuccess(message) {
    setStatus({ type: "success", message });
  }

  function showError(message) {
    setStatus({ type: "error", message });
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
      const detail = data?.detail || `Request failed with status ${response.status}`;
      throw new Error(detail);
    }

    return data;
  }

  async function runAction(action, successMessage) {
    try {
      setLoading(true);
      const result = await action();
      showSuccess(successMessage);
      return result;
    } catch (error) {
      showError(error.message);
      return null;
    } finally {
      setLoading(false);
    }
  }

  async function registerUser() {
    await runAction(
      () =>
        request("/users", {
          method: "POST",
          body: JSON.stringify(registerForm),
        }),
      "User created successfully"
    );
    await loadUsers();
  }

  async function login() {
    const data = await runAction(
      () =>
        request("/login", {
          method: "POST",
          body: JSON.stringify(loginForm),
        }),
      "Login succeeded"
    );

    if (data?.access_token) {
      setToken(data.access_token);
      localStorage.setItem("miniVaultToken", data.access_token);
    }
  }

  async function logout() {
    setToken("");
    setCurrentUser(null);
    setSafes([]);
    setSafeMembers([]);
    setAccounts([]);
    setAuditLogs([]);
    setRetrievedSecret(null);
    localStorage.removeItem("miniVaultToken");
    showSuccess("Logged out locally");
  }

  async function loadMe() {
    const data = await runAction(
      () => request("/me", { headers: authHeaders }),
      "Current user loaded"
    );
    if (data) setCurrentUser(data);
  }

  async function loadUsers() {
    const data = await runAction(() => request("/users"), "Users loaded");
    if (data) setUsers(data);
  }

  async function createSafe() {
    await runAction(
      () =>
        request("/safes", {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify(safeForm),
        }),
      "Safe created"
    );
    await loadSafes();
  }

  async function loadSafes() {
    const data = await runAction(
      () => request("/safes", { headers: authHeaders }),
      "Safes loaded"
    );
    if (data) {
      setSafes(data);
      if (data.length > 0 && !selectedSafeId) setSelectedSafeId(data[0].id);
    }
  }

  async function addMember() {
    if (!currentUser?.id) {
      showError("Load /me first so the frontend can send x-user-id for legacy endpoints");
      return;
    }

    await runAction(
      () =>
        request(`/safes/${selectedSafeId}/members`, {
          method: "POST",
          headers: { "x-user-id": currentUser.id },
          body: JSON.stringify(memberForm),
        }),
      "Member added to safe"
    );
    await loadMembers();
  }

  async function loadMembers() {
    if (!currentUser?.id) {
      showError("Load /me first so the frontend can send x-user-id for legacy endpoints");
      return;
    }

    const data = await runAction(
      () =>
        request(`/safes/${selectedSafeId}/members`, {
          headers: { "x-user-id": currentUser.id },
        }),
      "Safe members loaded"
    );
    if (data) setSafeMembers(data);
  }

  async function createAccount() {
    if (!currentUser?.id) {
      showError("Load /me first so the frontend can send x-user-id for legacy endpoints");
      return;
    }

    await runAction(
      () =>
        request(`/safes/${selectedSafeId}/accounts`, {
          method: "POST",
          headers: { "x-user-id": currentUser.id },
          body: JSON.stringify(accountForm),
        }),
      "Account created"
    );
    await loadAccounts();
  }

  async function loadAccounts() {
    if (!currentUser?.id) {
      showError("Load /me first so the frontend can send x-user-id for legacy endpoints");
      return;
    }

    const data = await runAction(
      () =>
        request(`/safes/${selectedSafeId}/accounts`, {
          headers: { "x-user-id": currentUser.id },
        }),
      "Accounts loaded"
    );
    if (data) setAccounts(data);
  }

  async function retrieveSecret(accountId) {
    if (!currentUser?.id) {
      showError("Load /me first so the frontend can send x-user-id for legacy endpoints");
      return;
    }

    const data = await runAction(
      () =>
        request(`/safes/${selectedSafeId}/accounts/${accountId}/retrieve`, {
          method: "POST",
          headers: { "x-user-id": currentUser.id },
        }),
      "Secret retrieved"
    );
    if (data) setRetrievedSecret(data);
  }

  async function loadAuditLogs() {
    if (!currentUser?.id) {
      showError("Load /me first so the frontend can send x-user-id for legacy endpoints");
      return;
    }

    const data = await runAction(
      () => request("/audit-logs", { headers: { "x-user-id": currentUser.id } }),
      "Audit logs loaded"
    );
    if (data) setAuditLogs(data);
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.14),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(59,130,246,0.12),_transparent_35%)]" />

      <main className="relative mx-auto max-w-7xl px-4 py-8">
        <motion.header
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8 flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-cyan-950/20 backdrop-blur md:flex-row md:items-center md:justify-between"
        >
          <div>
            <div className="mb-2 flex items-center gap-2 text-cyan-300">
              <Vault className="h-6 w-6" />
              <span className="text-sm font-semibold uppercase tracking-[0.25em]">
                Mini Vault
              </span>
            </div>
            <h1 className="text-3xl font-bold text-white md:text-5xl">
              Privileged Access Lab
            </h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-400 md:text-base">
              Interactive frontend for testing users, login, bearer tokens, safes,
              members, accounts, secret retrieval, and audit logs.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-700 bg-slate-950/80 p-4 text-sm">
            <div className="mb-2 flex items-center gap-2 text-slate-300">
              <Database className="h-4 w-4 text-cyan-300" />
              Backend
            </div>
            <div className="font-mono text-cyan-200">{API_BASE}</div>
            <div className="mt-3 flex items-center gap-2 text-slate-400">
              <KeyRound className="h-4 w-4" />
              {token ? `${token.slice(0, 18)}...` : "No token"}
            </div>
          </div>
        </motion.header>

        <div className="mb-6 grid gap-4 md:grid-cols-3">
          <Card className="border-slate-800 bg-slate-900/70 text-slate-100">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-cyan-300" />
                <div>
                  <div className="text-sm text-slate-400">Current user</div>
                  <div className="font-semibold">
                    {currentUser ? `${currentUser.username} (${currentUser.role})` : "Not loaded"}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/70 text-slate-100">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <Vault className="h-5 w-5 text-cyan-300" />
                <div>
                  <div className="text-sm text-slate-400">Safes loaded</div>
                  <div className="font-semibold">{safes.length}</div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/70 text-slate-100">
            <CardContent className="p-5">
              <div className="flex items-center gap-3">
                <Activity className="h-5 w-5 text-cyan-300" />
                <div>
                  <div className="text-sm text-slate-400">Audit logs loaded</div>
                  <div className="font-semibold">{auditLogs.length}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mb-6">
          <StatusBox status={status} />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Card className="border-slate-800 bg-slate-900/70 text-slate-100">
            <CardContent className="p-6">
              <SectionTitle
                icon={UserPlus}
                title="Register user"
                subtitle="Creates a user in the backend database"
              />
              <div className="grid gap-3 md:grid-cols-3">
                <Field
                  label="Username"
                  value={registerForm.username}
                  onChange={(value) => setRegisterForm({ ...registerForm, username: value })}
                />
                <Field
                  label="Role"
                  value={registerForm.role}
                  onChange={(value) => setRegisterForm({ ...registerForm, role: value })}
                  options={roles}
                />
                <Field
                  label="Password"
                  type="password"
                  value={registerForm.password}
                  onChange={(value) => setRegisterForm({ ...registerForm, password: value })}
                />
              </div>
              <Button onClick={registerUser} className="mt-4 rounded-xl">
                <Plus className="mr-2 h-4 w-4" />
                Create user
              </Button>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/70 text-slate-100">
            <CardContent className="p-6">
              <SectionTitle
                icon={LogIn}
                title="Login and identity"
                subtitle="Gets bearer token and calls /me"
              />
              <div className="grid gap-3 md:grid-cols-2">
                <Field
                  label="Username"
                  value={loginForm.username}
                  onChange={(value) => setLoginForm({ ...loginForm, username: value })}
                />
                <Field
                  label="Password"
                  type="password"
                  value={loginForm.password}
                  onChange={(value) => setLoginForm({ ...loginForm, password: value })}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={login} className="rounded-xl">
                  <KeyRound className="mr-2 h-4 w-4" />
                  Login
                </Button>
                <Button onClick={loadMe} variant="secondary" className="rounded-xl">
                  <Shield className="mr-2 h-4 w-4" />
                  Load /me
                </Button>
                <Button onClick={logout} variant="outline" className="rounded-xl border-slate-700 bg-slate-950">
                  Logout
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/70 text-slate-100 lg:col-span-2">
            <CardContent className="p-6">
              <SectionTitle
                icon={Vault}
                title="Safes"
                subtitle="Uses bearer token for /safes"
              />
              <div className="grid gap-3 md:grid-cols-3">
                <Field
                  label="Safe name"
                  value={safeForm.name}
                  onChange={(value) => setSafeForm({ ...safeForm, name: value })}
                />
                <Field
                  label="Safe type"
                  value={safeForm.safe_type}
                  onChange={(value) => setSafeForm({ ...safeForm, safe_type: value })}
                  options={safeTypes}
                />
                <Field
                  label="Description"
                  value={safeForm.description}
                  onChange={(value) => setSafeForm({ ...safeForm, description: value })}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={createSafe} className="rounded-xl">
                  <Plus className="mr-2 h-4 w-4" />
                  Create safe
                </Button>
                <Button onClick={loadSafes} variant="secondary" className="rounded-xl">
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Load safes
                </Button>
              </div>

              <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {safes.map((safe) => (
                  <button
                    key={safe.id}
                    onClick={() => setSelectedSafeId(safe.id)}
                    className={`rounded-2xl border p-4 text-left transition ${
                      selectedSafeId === safe.id
                        ? "border-cyan-400 bg-cyan-400/10"
                        : "border-slate-800 bg-slate-950 hover:border-slate-600"
                    }`}
                  >
                    <div className="font-semibold text-white">{safe.name}</div>
                    <div className="mt-1 text-sm text-slate-400">{safe.id}</div>
                    <div className="mt-2 text-xs text-cyan-300">{safe.safe_type}</div>
                    <p className="mt-2 text-sm text-slate-400">{safe.description}</p>
                  </button>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/70 text-slate-100">
            <CardContent className="p-6">
              <SectionTitle
                icon={Users}
                title="Safe members"
                subtitle="Legacy endpoints use x-user-id from /me"
              />
              <Field label="Selected safe id" value={selectedSafeId} onChange={setSelectedSafeId} />
              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <Field
                  label="User id"
                  value={memberForm.user_id}
                  onChange={(value) => setMemberForm({ ...memberForm, user_id: value })}
                />
                <Field
                  label="Permission"
                  value={memberForm.permission_level}
                  onChange={(value) => setMemberForm({ ...memberForm, permission_level: value })}
                  options={permissionLevels}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={addMember} className="rounded-xl">
                  Add member
                </Button>
                <Button onClick={loadMembers} variant="secondary" className="rounded-xl">
                  Load members
                </Button>
              </div>
              <div className="mt-4 space-y-2">
                {safeMembers.map((member) => (
                  <div key={`${member.safe_id}-${member.user_id}`} className="rounded-xl bg-slate-950 p-3 text-sm">
                    <span className="font-mono text-cyan-300">{member.user_id}</span>
                    <span className="mx-2 text-slate-600">|</span>
                    <span>{member.permission_level}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/70 text-slate-100">
            <CardContent className="p-6">
              <SectionTitle
                icon={Lock}
                title="Accounts and secrets"
                subtitle="Create account metadata and retrieve secret"
              />
              <div className="grid gap-3 md:grid-cols-2">
                <Field
                  label="Username"
                  value={accountForm.username}
                  onChange={(value) => setAccountForm({ ...accountForm, username: value })}
                />
                <Field
                  label="Target"
                  value={accountForm.target}
                  onChange={(value) => setAccountForm({ ...accountForm, target: value })}
                />
                <Field
                  label="Platform"
                  value={accountForm.platform}
                  onChange={(value) => setAccountForm({ ...accountForm, platform: value })}
                  options={platforms}
                />
                <Field
                  label="Secret value"
                  value={accountForm.secret_value}
                  onChange={(value) => setAccountForm({ ...accountForm, secret_value: value })}
                />
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button onClick={createAccount} className="rounded-xl">
                  Create account
                </Button>
                <Button onClick={loadAccounts} variant="secondary" className="rounded-xl">
                  Load accounts
                </Button>
              </div>
              <div className="mt-4 space-y-2">
                {accounts.map((account) => (
                  <div key={account.id} className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-semibold text-white">{account.username}</div>
                        <div className="text-sm text-slate-400">{account.id} on {account.target}</div>
                        <div className="mt-1 text-xs text-cyan-300">{account.platform}</div>
                      </div>
                      <Button size="sm" onClick={() => retrieveSecret(account.id)} className="rounded-xl">
                        <Eye className="mr-2 h-4 w-4" />
                        Retrieve
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
              {retrievedSecret && (
                <div className="mt-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-4">
                  <div className="text-sm text-emerald-200">Retrieved secret</div>
                  <div className="mt-2 font-mono text-lg text-white">{retrievedSecret.secret_value}</div>
                  <div className="mt-1 text-xs text-emerald-300">
                    Account: {retrievedSecret.account_id} | Version: {retrievedSecret.secret_version}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-slate-800 bg-slate-900/70 text-slate-100 lg:col-span-2">
            <CardContent className="p-6">
              <SectionTitle
                icon={Activity}
                title="Audit logs"
                subtitle="Admin-only view of secret retrieval attempts"
              />
              <Button onClick={loadAuditLogs} variant="secondary" className="mb-4 rounded-xl">
                <RefreshCw className="mr-2 h-4 w-4" />
                Load audit logs
              </Button>
              <div className="overflow-hidden rounded-2xl border border-slate-800">
                <table className="w-full text-left text-sm">
                  <thead className="bg-slate-950 text-xs uppercase text-slate-400">
                    <tr>
                      <th className="px-4 py-3">ID</th>
                      <th className="px-4 py-3">Actor</th>
                      <th className="px-4 py-3">Action</th>
                      <th className="px-4 py-3">Success</th>
                      <th className="px-4 py-3">Message</th>
                      <th className="px-4 py-3">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.id} className="border-t border-slate-800 bg-slate-950/60">
                        <td className="px-4 py-3 font-mono text-cyan-300">{log.id}</td>
                        <td className="px-4 py-3">{log.actor_user_id}</td>
                        <td className="px-4 py-3">{log.action}</td>
                        <td className="px-4 py-3">{String(log.success)}</td>
                        <td className="px-4 py-3 text-slate-300">{log.message}</td>
                        <td className="px-4 py-3 text-slate-400">{log.time || "-"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="mt-8 rounded-3xl border border-slate-800 bg-slate-900/70 p-6 text-sm text-slate-400">
          <div className="mb-2 flex items-center gap-2 text-slate-200">
            <AlertTriangle className="h-4 w-4 text-amber-300" />
            Development note
          </div>
          Some backend endpoints currently use bearer token authentication, while older endpoints still use x-user-id.
          This frontend supports both so you can continue the migration gradually.
        </div>
      </main>

      {loading && (
        <div className="fixed bottom-4 right-4 rounded-2xl border border-cyan-400/40 bg-slate-950 px-4 py-3 text-sm text-cyan-200 shadow-xl">
          Running request...
        </div>
      )}
    </div>
  );
}
