'use client';

import { useState } from 'react';

export default function AdminLogin() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const res = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        window.location.reload();
      } else {
        setError('비밀번호가 올바르지 않습니다');
      }
    } catch {
      setError('로그인에 실패했습니다');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: '#f5f5f7' }}>
      <form
        onSubmit={handleSubmit}
        className="w-full flex flex-col gap-4"
        style={{
          maxWidth: '360px',
          padding: '40px',
          backgroundColor: '#ffffff',
          borderRadius: '18px',
          border: '1px solid #d2d2d7',
        }}
      >
        <div className="text-center">
          <h1
            className="text-[24px] font-semibold"
            style={{ color: '#1d1d1f', letterSpacing: '-0.3px' }}
          >
            Admin
          </h1>
          <p className="text-[14px] mt-1" style={{ color: '#6e6e73' }}>
            OpenSAC 백오피스
          </p>
        </div>

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="비밀번호"
          autoFocus
          className="w-full px-4 transition-colors"
          style={{
            height: '44px',
            borderRadius: '10px',
            border: '1px solid #d2d2d7',
            backgroundColor: '#ffffff',
            color: '#1d1d1f',
            fontSize: '15px',
            outline: 'none',
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = '#0071e3';
            e.currentTarget.style.boxShadow = '0 0 0 3px rgba(0,113,227,0.15)';
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = '#d2d2d7';
            e.currentTarget.style.boxShadow = 'none';
          }}
        />

        {error && (
          <p className="text-[13px] text-center" style={{ color: '#ff3b30' }}>
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading || !password}
          className="w-full transition-colors"
          style={{
            height: '44px',
            borderRadius: '10px',
            backgroundColor: loading || !password ? '#86868b' : '#0071e3',
            color: '#ffffff',
            fontSize: '15px',
            fontWeight: 600,
            border: 'none',
            cursor: loading || !password ? 'default' : 'pointer',
          }}
        >
          {loading ? '로그인 중...' : '로그인'}
        </button>
      </form>
    </div>
  );
}
