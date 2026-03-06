import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, textAlign: 'center', fontFamily: 'system-ui, sans-serif' }}>
          <h1 style={{ fontSize: 24, marginBottom: 8 }}>Something went wrong</h1>
          <p style={{ color: '#6B7280', marginBottom: 16 }}>
            An unexpected error occurred. Please reload the page.
          </p>
          <pre style={{ background: '#F3F4F6', padding: 16, borderRadius: 8, textAlign: 'left', maxWidth: 600, margin: '0 auto', overflow: 'auto', fontSize: 13 }}>
            {this.state.error?.message}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{ marginTop: 20, padding: '8px 20px', background: '#2563EB', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14 }}
          >
            Reload Page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
