'use client';

import { useState } from 'react';

export default function AccountPage() {
  const [email, setEmail] = useState('');
  const [allowEmails, setAllowEmails] = useState(true);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      // TODO: Connect to backend API once it's ready.
      // Example: POST `${NEXT_PUBLIC_API_BASE_URL}/api/account/settings`
      // body: { email, allowEmails }
      await new Promise((r) => setTimeout(r, 350));
      alert('Settings saved.');
    } catch (err) {
      alert('Error occurred while savingwhile saving.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Account & Privacy</h1>

      <form onSubmit={handleSubmit} className="space-y-4 max-w-md">
        <div>
          <label htmlFor="email" className="block text-sm font-medium">
            Email
          </label>
          <input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            id="allowEmails"
            type="checkbox"
            checked={allowEmails}
            onChange={(e) => setAllowEmails(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300"
          />
          <label htmlFor="allowEmails" className="text-sm">
            Receive product updates and notifications
          </label>
        </div>

        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-60"
        >
          {saving ? 'Saving…' : 'Save'}
        </button>
      </form>

      <section className="pt-6 border-t space-y-2 max-w-md">
        <h2 className="text-lg font-semibold">Privacy Actions (MVP)</h2>
        <p className="text-sm text-gray-600">
          TODO: 데이터 export / delete 요청 UI를 여기에 붙일 수 있어요.
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className="rounded-md border px-3 py-2 text-sm hover:bg-gray-50"
            onClick={() => alert('TODO: Export data')}
          >
            Export my data
          </button>
          <button
            type="button"
            className="rounded-md border border-red-300 px-3 py-2 text-sm text-red-700 hover:bg-red-50"
            onClick={() => alert('TODO: Delete my data')}
          >
            Delete my data
          </button>
        </div>
      </section>
    </main>
  );
}
