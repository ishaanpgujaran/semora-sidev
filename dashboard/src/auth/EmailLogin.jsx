/**
 * @file EmailLogin.jsx
 * @description Standard email/password forms supporting login and register events in Firebase Auth.
 */

import React, { useState } from 'react';

export default function EmailLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // TODO(frontend-agent): Wire credentials to Firebase login/register routines.
  return (
    <form className="login-form" onSubmit={(e) => e.preventDefault()}>
      <h2>Login</h2>
      <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <button type="submit">Sign In</button>
    </form>
  );
}
