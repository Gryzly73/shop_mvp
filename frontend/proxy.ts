import os from 'node:os';

import { NextResponse } from 'next/server';

export function proxy() {
  const response = NextResponse.next();
  response.headers.set('X-Instance', os.hostname());
  return response;
}
