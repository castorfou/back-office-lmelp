import { describe, it, expect } from 'vitest';
import { checkBabelioCookie } from '../babelioCookie.js';

// Même structure qu'un en-tête Cookie réel copié depuis Firefox, valeurs factices.
const FIREFOX_COOKIE =
  'g_state={"i_l":1,"i_ll":1700000000000,"i_e":{"enable_itp_optimization":24},' +
  '"i_et":1700000000000,"i_b":"AAAA/bbbb+CCCC"}; bbacml=0; ' +
  'bbac=00000000000000000000000000000000; id_user=1; disclaimer=1; ' +
  '_ga_XXXXXXXXXX=GS2.1.s1700000000$o1$g0$t1700000000$j38$l0$h0; ' +
  '_ga=GA1.2.123.456; jstsToken=AbCd%2FeF%2BgH%3D%3D; PHPSESSID=fakesession123';

describe('checkBabelioCookie', () => {
  it('accepte un en-tête Cookie copié depuis Firefox', () => {
    expect(checkBabelioCookie(`  ${FIREFOX_COOKIE}  `)).toEqual({ value: FIREFOX_COOKIE, error: null });
  });

  it('retire un préfixe « Cookie: » collé par mégarde', () => {
    expect(checkBabelioCookie('Cookie: jstsToken=AbCd; p=FR')).toEqual({
      value: 'jstsToken=AbCd; p=FR',
      error: null,
    });
  });

  it.each([
    ['User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0', 'en-tête Cookie'],
    ['Set-Cookie', 'jstsToken=AbCd; path=/; expires=Sat, 15 Nov 2026 12:00:00 GMT; HttpOnly', 'Set-Cookie'],
    ['plusieurs lignes', 'Host: www.babelio.com\nCookie: jstsToken=AbCd; p=FR', 'Plusieurs lignes'],
    ['jeton seul', 'AbCd%2FeF%2BgH%3D%3D', 'en-tête Cookie'],
    ['sans jstsToken', 'disclaimer=1; p=FR; PHPSESSID=fakesession123', 'jstsToken absent'],
    ['jstsToken vide', 'jstsToken=; disclaimer=1', 'jstsToken absent'],
  ])('refuse : %s', (_label, pasted, expected) => {
    const { error } = checkBabelioCookie(pasted);
    expect(error).toContain(expected);
  });
});
