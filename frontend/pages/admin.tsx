import { useEffect, useState } from 'react';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
const WAG_URL = process.env.NEXT_PUBLIC_WAG_URL || 'http://localhost:3001';

interface Stats {
  total_documents: number;
  total_urls: number;
  total_chats: number;
  total_vectors: number;
}

interface ApiEntry {
  id: number;
  name: string;
  url: string;
  method: string;
}

export default function Admin() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [documents, setDocuments] = useState<any[]>([]);
  const [apis, setApis] = useState<ApiEntry[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState('');
  const [waQr, setWaQr] = useState<string | null>(null);
  const [waReady, setWaReady] = useState<boolean | null>(null);

  useEffect(() => {
    fetchStats();
    fetchDocuments();
    fetchApis();
    fetchWaStatus();
  }, []);

  const fetchStats = async () => {
    const response = await fetch(`${BACKEND_URL}/stats`);
    if (response.ok) setStats(await response.json());
  };

  const fetchDocuments = async () => {
    const response = await fetch(`${BACKEND_URL}/documents`);
    if (response.ok) setDocuments(await response.json());
  };

  const fetchApis = async () => {
    const response = await fetch(`${BACKEND_URL}/apis`);
    if (response.ok) setApis(await response.json());
  };

  const fetchWaQr = async () => {
    try {
      const res = await fetch(`${WAG_URL}/qr`);
      const data = await res.json();
      setWaQr(data.qr || null);
      setWaReady(data.ready || false);
    } catch (e) {
      setWaQr(null);
    }
  };

  const fetchWaStatus = async () => {
    try {
      const res = await fetch(`${WAG_URL}/status`);
      const data = await res.json();
      setWaReady(data.ready || false);
    } catch (e) {
      setWaReady(false);
    }
  };

  const uploadFile = async () => {
    if (!selectedFile) return;
    const formData = new FormData();
    formData.append('file', selectedFile);
    const response = await fetch(`${BACKEND_URL}/upload`, { method: 'POST', body: formData });
    if (response.ok) {
      setUploadMessage('Upload successful');
      setSelectedFile(null);
      fetchDocuments();
      fetchStats();
    } else {
      setUploadMessage('Upload failed.');
    }
  };

  const deleteDocument = async (id: number) => {
    await fetch(`${BACKEND_URL}/document/${id}`, { method: 'DELETE' });
    fetchDocuments();
    fetchStats();
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl p-6">
        <div className="mb-6 flex items-center justify-between rounded-3xl bg-slate-900 p-6 shadow-lg shadow-black/20">
          <div>
            <h1 className="text-3xl font-semibold">Admin Dashboard</h1>
            <p className="mt-2 text-slate-400">Manage documents, webhook APIs, and application settings.</p>
          </div>
          <a href="/" className="rounded-3xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950">Go to Chat</a>
        </div>

        <section className="grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl bg-slate-900 p-6 shadow-lg shadow-black/20">
            <h2 className="mb-4 text-xl font-semibold">Overview</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                <div className="text-sm text-slate-500">Documents</div>
                <div className="mt-2 text-3xl font-semibold">{stats?.total_documents ?? '—'}</div>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                <div className="text-sm text-slate-500">URLs</div>
                <div className="mt-2 text-3xl font-semibold">{stats?.total_urls ?? '—'}</div>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                <div className="text-sm text-slate-500">Chats</div>
                <div className="mt-2 text-3xl font-semibold">{stats?.total_chats ?? '—'}</div>
              </div>
              <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                <div className="text-sm text-slate-500">Vectors</div>
                <div className="mt-2 text-3xl font-semibold">{stats?.total_vectors ?? '—'}</div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl bg-slate-900 p-6 shadow-lg shadow-black/20">
            <h2 className="mb-4 text-xl font-semibold">Upload Knowledge</h2>
            <input
              type="file"
              className="w-full rounded-2xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-100"
              onChange={(event) => setSelectedFile(event.target.files?.[0] || null)}
            />
            <button onClick={uploadFile} className="mt-4 rounded-3xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-400">
              Upload File
            </button>
            {uploadMessage && <p className="mt-3 text-sm text-slate-300">{uploadMessage}</p>}
          </div>
        </section>

        <section className="mt-6 rounded-3xl bg-slate-900 p-6 shadow-lg shadow-black/20">
          <h2 className="mb-4 text-xl font-semibold">Documents</h2>
          <div className="space-y-3">
            {documents.length === 0 ? (
              <p className="text-slate-500">No documents yet.</p>
            ) : (
              documents.map((doc) => (
                <div key={doc.id} className="flex flex-col gap-2 rounded-3xl border border-slate-800 bg-slate-950 p-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="font-medium">{doc.title}</div>
                    <div className="text-sm text-slate-500">{doc.source} · {doc.doc_type}</div>
                  </div>
                  <button onClick={() => deleteDocument(doc.id)} className="rounded-2xl bg-red-500 px-4 py-2 text-sm font-semibold text-white hover:bg-red-400">
                    Delete
                  </button>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="mt-6 rounded-3xl bg-slate-900 p-6 shadow-lg shadow-black/20">
          <h2 className="mb-4 text-xl font-semibold">API Triggers</h2>
          <p className="mb-4 text-sm text-slate-400">Use /runapi &lt;id|name&gt; in chat to invoke registered APIs.</p>
          {apis.length === 0 ? (
            <p className="text-slate-500">No APIs configured yet.</p>
          ) : (
            <div className="space-y-3">
              {apis.map((api) => (
                <div key={api.id} className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
                  <div className="font-medium">{api.name}</div>
                  <div className="mt-1 text-sm text-slate-500">{api.method} • {api.url}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="mt-6 rounded-3xl bg-slate-900 p-6 shadow-lg shadow-black/20">
          <h2 className="mb-4 text-xl font-semibold">WhatsApp Gateway</h2>
          <p className="mb-4 text-sm text-slate-400">Scan the QR with your phone's WhatsApp to connect (self-hosted, no third-party).</p>
          <div className="space-y-3">
            <div className="rounded-3xl border border-slate-800 bg-slate-950 p-4">
              <div className="font-medium">Status: <span className="text-sm text-slate-500">{waReady ? 'Connected' : 'Disconnected'}</span></div>
              <div className="mt-3">
                {waQr ? (
                  <img src={waQr} alt="whatsapp-qr" className="w-64" />
                ) : (
                  <p className="text-sm text-slate-500">No QR available. Click refresh to request a QR.</p>
                )}
              </div>
              <div className="mt-4 flex gap-2">
                <button onClick={fetchWaQr} className="rounded-2xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400">Refresh QR</button>
                <button onClick={fetchWaStatus} className="rounded-2xl bg-slate-800 px-4 py-2 text-sm font-semibold text-slate-200">Check Status</button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
