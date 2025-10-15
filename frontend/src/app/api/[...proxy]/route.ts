import { NextRequest, NextResponse } from 'next/server';

/**
 * API Proxy Route Handler
 * 
 * This catches all requests to /api/* and forwards them to the FastAPI backend.
 * Benefits:
 * - Backend URL is hidden (server-side only env var)
 * - Supports httpOnly cookies
 * - Consistent behavior for SSR and CSR
 * - Can add middleware (rate limiting, logging, etc.)
 */

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

// Helper to check if we should skip proxying (e.g., for Next.js internal routes)
function shouldProxy(pathname: string): boolean {
  // Skip Next.js internal API routes
  if (pathname.startsWith('/api/_next')) return false;
  return true;
}

/**
 * Forward headers from client to backend, excluding hop-by-hop headers
 */
function getProxyHeaders(request: NextRequest): HeadersInit {
  const headers: HeadersInit = {};
  
  // Copy relevant headers
  request.headers.forEach((value, key) => {
    // Skip hop-by-hop headers
    const hopByHopHeaders = [
      'connection',
      'keep-alive',
      'proxy-authenticate',
      'proxy-authorization',
      'te',
      'trailers',
      'transfer-encoding',
      'upgrade',
      'host', // We'll set this to backend host
    ];
    
    if (!hopByHopHeaders.includes(key.toLowerCase())) {
      headers[key] = value;
    }
  });
  
  // Set host to backend
  headers['host'] = new URL(BACKEND_URL).host;
  
  return headers;
}

/**
 * GET handler
 */
export async function GET(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  if (!shouldProxy(pathname)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  
  // Remove /api prefix and construct backend URL
  const backendPath = pathname.replace(/^\/api/, '');
  const searchParams = request.nextUrl.searchParams.toString();
  const backendUrl = `${BACKEND_URL}${backendPath}${searchParams ? `?${searchParams}` : ''}`;
  
  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: getProxyHeaders(request),
      // Forward cookies
      credentials: 'include',
    });
    
    // Handle 204 No Content - cannot have a body
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        statusText: response.statusText,
        headers: response.headers,
      });
    }
    
    // Get response body
    const data = await response.arrayBuffer();
    
    // Forward response with headers
    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    );
  }
}

/**
 * POST handler
 */
export async function POST(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  if (!shouldProxy(pathname)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  
  const backendPath = pathname.replace(/^\/api/, '');
  const searchParams = request.nextUrl.searchParams.toString();
  const backendUrl = `${BACKEND_URL}${backendPath}${searchParams ? `?${searchParams}` : ''}`;
  
  try {
    // Get request body
    const body = await request.arrayBuffer();
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: getProxyHeaders(request),
      body: body.byteLength > 0 ? body : undefined,
      credentials: 'include',
    });
    
    // Handle 204 No Content - cannot have a body
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        statusText: response.statusText,
        headers: response.headers,
      });
    }
    
    const data = await response.arrayBuffer();
    
    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    );
  }
}

/**
 * PUT handler
 */
export async function PUT(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  if (!shouldProxy(pathname)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  
  const backendPath = pathname.replace(/^\/api/, '');
  const searchParams = request.nextUrl.searchParams.toString();
  const backendUrl = `${BACKEND_URL}${backendPath}${searchParams ? `?${searchParams}` : ''}`;
  
  try {
    const body = await request.arrayBuffer();
    
    const response = await fetch(backendUrl, {
      method: 'PUT',
      headers: getProxyHeaders(request),
      body: body.byteLength > 0 ? body : undefined,
      credentials: 'include',
    });
    
    // Handle 204 No Content - cannot have a body
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        statusText: response.statusText,
        headers: response.headers,
      });
    }
    
    const data = await response.arrayBuffer();
    
    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    );
  }
}

/**
 * DELETE handler
 */
export async function DELETE(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  if (!shouldProxy(pathname)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  
  const backendPath = pathname.replace(/^\/api/, '');
  const searchParams = request.nextUrl.searchParams.toString();
  const backendUrl = `${BACKEND_URL}${backendPath}${searchParams ? `?${searchParams}` : ''}`;
  
  try {
    const response = await fetch(backendUrl, {
      method: 'DELETE',
      headers: getProxyHeaders(request),
      credentials: 'include',
    });
    
    // Handle 204 No Content - cannot have a body
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        statusText: response.statusText,
        headers: response.headers,
      });
    }
    
    const data = await response.arrayBuffer();
    
    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    );
  }
}

/**
 * PATCH handler
 */
export async function PATCH(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  if (!shouldProxy(pathname)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }
  
  const backendPath = pathname.replace(/^\/api/, '');
  const searchParams = request.nextUrl.searchParams.toString();
  const backendUrl = `${BACKEND_URL}${backendPath}${searchParams ? `?${searchParams}` : ''}`;
  
  try {
    const body = await request.arrayBuffer();
    
    const response = await fetch(backendUrl, {
      method: 'PATCH',
      headers: getProxyHeaders(request),
      body: body.byteLength > 0 ? body : undefined,
      credentials: 'include',
    });
    
    // Handle 204 No Content - cannot have a body
    if (response.status === 204) {
      return new NextResponse(null, {
        status: 204,
        statusText: response.statusText,
        headers: response.headers,
      });
    }
    
    const data = await response.arrayBuffer();
    
    return new NextResponse(data, {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return NextResponse.json(
      { error: 'Backend service unavailable' },
      { status: 503 }
    );
  }
}
