/** Purpose: Verify successful-session login routing and safe callback destinations. */
import assert from 'node:assert/strict';
import { authConfig } from '../src/auth.config.js';
const baseUrl = 'https://workshop.acm.is';
for (const url of ['/login', '/login?callbackUrl=/login', 'https://elsewhere.example/', '//elsewhere.example/']) assert.equal(authConfig.callbacks.redirect({ url, baseUrl }), baseUrl + '/');
assert.equal(authConfig.callbacks.redirect({ url: '/?view=cockpit-reconstruct', baseUrl }), baseUrl + '/?view=cockpit-reconstruct');
const response = authConfig.callbacks.authorized({ auth: { user: { id: 'fixture' } }, request: { nextUrl: new URL(baseUrl + '/login') } });
assert.equal(response.headers.get('location'), baseUrl + '/');
assert.equal(authConfig.callbacks.authorized({ auth: null, request: { nextUrl: new URL(baseUrl + '/login') } }), true);
console.log('PASS: login callbacks, signed-in home redirect and external redirect rejection.');
