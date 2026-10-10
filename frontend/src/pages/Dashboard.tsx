import { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { Activity, AlertTriangle, CheckCircle2, ChevronDown, CircleStop, FileVideo2, Play, Radio, Upload, Users, Video } from 'lucide-react';

const API = import.meta.env.VITE_API_BASE ?? '';
type SystemState = { processing: boolean; fps: number; total_objects: number; unique_objects: number; objects_by_class: Record<string, number>; current_objects_by_class: Record<string, number>; current_detections: { track_id: string; class: string; confidence: number; bbox: number[] }[]; frame_width: number; frame_height: number; active_alerts: number; risk_score: number; risk_level: string; risk_reason: string; current_video?: string | null; frame_count?: number };
type Event = { id: number; type: string; severity: string; timestamp: string; reason: string; risk_score: number };
type Report = { title: string; summary: string; highlights: string[]; is_demo: boolean };
const samples = [
  { name: 'Street camera', file: 'cctv_street_sample.mp4', duration: '00:10', kind: 'People + traffic' },
  { name: 'Crowd gathering', file: 'demo_crowd.mp4', duration: '00:15', kind: 'Crowd density' },
  { name: 'Loitering', file: 'demo_loitering.mp4', duration: '00:20', kind: 'Stationary activity' },
  { name: 'Pedestrian proximity', file: 'demo_proximity.mp4', duration: '00:15', kind: 'Vehicle proximity' },
  { name: 'Restricted zone', file: 'demo_perimeter.mp4', duration: '00:18', kind: 'Zone entry' },
  { name: 'Unattended object', file: 'demo_unattended.mp4', duration: '00:18', kind: 'Object monitoring' },
];

export default function Dashboard() {
  const [state, setState] = useState<SystemState>({ processing: false, fps: 0, total_objects: 0, unique_objects: 0, objects_by_class: {}, current_objects_by_class: {}, current_detections: [], frame_width: 0, frame_height: 0, active_alerts: 0, risk_score: 0, risk_level: 'LOW', risk_reason: '' });
  const [events, setEvents] = useState<Event[]>([]);
  const [report, setReport] = useState<Report>({ title: 'Session summary', summary: 'Choose a sample clip or upload footage to begin analysis.', highlights: [], is_demo: false });
  const [modules, setModules] = useState<Record<string, boolean>>({});
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedSample, setSelectedSample] = useState('');
  const [videoElement, setVideoElement] = useState<HTMLVideoElement | null>(null);

  const refresh = async () => {
    try {
      const [s, e, r] = await Promise.all([axios.get(`${API}/api/analysis/status`), axios.get(`${API}/api/events?limit=8`), axios.get(`${API}/api/analysis/report`)]);
      const d = s.data;
      setState({ processing: d.processing ?? d.running ?? false, fps: d.fps ?? 0, total_objects: d.total_objects ?? d.objects ?? 0, unique_objects: d.unique_objects ?? 0, objects_by_class: d.objects_by_class ?? {}, current_objects_by_class: d.current_objects_by_class ?? {}, current_detections: d.current_detections ?? [], frame_width: d.frame_width ?? 0, frame_height: d.frame_height ?? 0, active_alerts: d.active_alerts ?? 0, risk_score: d.risk_score ?? 0, risk_level: d.risk_level ?? 'LOW', risk_reason: d.risk_reason ?? '', current_video: d.current_video, frame_count: d.frame_count ?? 0 });
      setEvents((e.data ?? []).map((v: any) => ({ ...v, id: v.id ?? 0, reason: v.reason ?? '', severity: v.severity ?? 'LOW' })));
      setReport(r.data);
    } catch { /* The inline connection indicator communicates backend state. */ }
  };
  useEffect(() => {
    refresh();
    axios.get(`${API}/api/health`).then(({ data }) => setModules(data.modules ?? {})).catch(() => {});
    const id = window.setInterval(refresh, 1200);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => {
    if (state.processing && videoUrl && videoElement) videoElement.play().catch(() => {});
  }, [state.processing, videoUrl, videoElement]);
  useEffect(() => {
    if (!selectedFile) return;
    const url = URL.createObjectURL(selectedFile);
    setVideoUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  const activeSource = useMemo(() => selectedSample ? samples.find(s => s.file === selectedSample)?.name : selectedFile?.name, [selectedSample, selectedFile]);
  const chooseSample = (file: string) => { setSelectedSample(file); setSelectedFile(null); setVideoUrl(`${API}/demo-videos/${file}`); setError(''); };
  const onSelectFile = (file?: File) => { if (!file) return; setSelectedFile(file); setSelectedSample(''); setError(''); };
  const start = async (sample?: string) => {
    const sampleToRun = sample ?? selectedSample;
    setError(''); setBusy(true);
    try {
      if (sampleToRun) {
        const url = `${API}/demo-videos/${sampleToRun}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error('Could not load this sample clip.');
        const blob = await res.blob();
        const form = new FormData(); form.append('file', blob, sampleToRun);
        const uploaded = await axios.post(`${API}/api/video/upload`, form);
        if (uploaded.data.preview_url) setVideoUrl(`${API}${uploaded.data.preview_url}`);
        await axios.post(`${API}/api/analysis/start`, { source: 'upload', video_path: uploaded.data.filename, demo_mode: false });
      } else if (selectedFile) {
        const form = new FormData(); form.append('file', selectedFile);
        const uploaded = await axios.post(`${API}/api/video/upload`, form);
        if (uploaded.data.preview_url) setVideoUrl(`${API}${uploaded.data.preview_url}`);
        await axios.post(`${API}/api/analysis/start`, { source: 'upload', video_path: uploaded.data.filename, demo_mode: false });
      } else {
        await axios.post(`${API}/api/analysis/start`, { source: 'demo', demo_mode: true });
      }
      await refresh();
      videoElement?.play().catch(() => {});
    } catch (e: unknown) {
      const detail = axios.isAxiosError(e) ? e.response?.data?.detail : (e as Error).message;
      setError(typeof detail === 'string' ? detail : 'Could not start analysis. Check the video file and backend connection.');
    } finally { setBusy(false); }
  };
  const stop = async () => { try { await axios.post(`${API}/api/analysis/stop`); await refresh(); } catch { setError('Unable to stop the current analysis.'); } };
  const severityClass = (v: string) => v.toLowerCase();

  return <main className="civis-shell">
    <header className="topbar">
      <a className="brand" href="#"><span className="brand-mark"><Activity size={19}/></span><span><b>CIVIS</b><small>VIDEO INTELLIGENCE</small></span></a>
      <div className="topbar-right"><span className="source-label"><Radio size={14}/> {activeSource ?? 'NO SOURCE SELECTED'}</span><span className={`connection ${modules.detection ? 'online' : ''}`}><i/>{modules.detection ? 'SYSTEM ONLINE' : 'CONNECTING'}</span></div>
    </header>

    <section className="page-heading"><div><div className="eyebrow">MONITORING CONSOLE <span> / </span> SESSION 01</div><h1>Video analysis</h1><p>Review footage and monitor detections as they are processed.</p></div><div className={`session-badge ${state.processing ? 'is-live' : ''}`}><i/>{state.processing ? 'ANALYSIS IN PROGRESS' : 'READY FOR FOOTAGE'}</div></section>
    {error && <div className="inline-error" role="alert"><AlertTriangle size={16}/><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss">×</button></div>}

    <div className="workspace-grid">
      <section className="panel viewer-panel">
        <div className="panel-heading"><div><span className="overline">CAMERA FEED</span><h2>{activeSource ?? 'Select footage to preview'}</h2></div><div className="feed-meta"><span className={state.processing ? 'tag-live' : 'tag-ready'}><i/>{state.processing ? 'LIVE ANALYSIS' : 'PREVIEW'}</span><span>HD · LOCAL</span></div></div>
        <div className="viewer">
          {videoUrl ? <video ref={setVideoElement} key={videoUrl} src={videoUrl} controls playsInline preload="metadata" onError={() => setError('This clip could not be decoded for preview. Choose an MP4, MOV, AVI or MKV video.')} /> : <div className="viewer-empty"><div className="empty-icon"><Video size={24}/></div><b>Footage preview</b><span>Select a sample or upload a video to view it here.</span></div>}
          {videoUrl && state.frame_width > 0 && state.frame_height > 0 && <svg className="detections-overlay" viewBox={`0 0 ${state.frame_width} ${state.frame_height}`} preserveAspectRatio="xMidYMid meet" aria-label="Current object detections">{state.current_detections.map(d => { const [x1, y1, x2, y2] = d.bbox; return <g key={d.track_id}><rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill="none" stroke="#64d5a6" strokeWidth={Math.max(2, state.frame_width / 700)}/><text x={x1} y={Math.max(14, y1 - 4)} fill="#baf1d7" fontSize={Math.max(13, state.frame_width / 70)} paintOrder="stroke" stroke="#06100c" strokeWidth="3">{d.class.toUpperCase()} {Math.round(d.confidence * 100)}%</text></g>; })}</svg>}
          {videoUrl && <><div className="hud hud-top"><span>CAM 01 <b>·</b> {activeSource ?? 'LOCAL UPLOAD'}</span><span>{state.processing ? <><i className="pulse-dot"/> REC</> : 'READY'}</span></div><div className="hud hud-bottom"><span>FRAME {String(state.frame_count ?? 0).padStart(6, '0')}</span><span>{state.fps.toFixed(1)} FPS <b>·</b> {state.total_objects} TRACKED</span></div></>}
        </div>
        <div className="viewer-actions"><label className="button button-subtle" htmlFor="video-upload"><Upload size={15}/> Upload video</label><input id="video-upload" type="file" accept="video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,video/*" onChange={e => onSelectFile(e.target.files?.[0])}/><button className="button button-primary" disabled={busy || state.processing} onClick={() => start(selectedSample || (!selectedFile ? samples[0].file : undefined))}><Play size={15}/>{busy ? 'Preparing…' : selectedFile || selectedSample ? 'Analyze footage' : 'Start demo'}</button>{state.processing && <button className="button button-stop" onClick={stop}><CircleStop size={15}/> Stop</button>}<span className="action-hint">{selectedFile ? selectedFile.name : 'MP4 · MOV · AVI · MKV'}</span></div>
      </section>

      <aside className="side-stack">
        <section className={`panel risk-panel risk-${state.risk_level.toLowerCase()}`}><div className="panel-heading small-heading"><div><span className="overline">SESSION RISK</span><h2>{state.risk_level}</h2></div><div className="risk-score">{Math.round(state.risk_score)}<small>/100</small></div></div><div className="risk-track"><i style={{ width: `${Math.min(100, Math.max(0, state.risk_score))}%` }}/></div><p>{state.risk_reason || (state.active_alerts ? `${state.active_alerts} distinct incident rule${state.active_alerts === 1 ? '' : 's'} triggered` : state.processing ? 'No incident rules triggered so far' : 'No incident rules triggered in this session')}</p></section>
        <section className="panel telemetry-panel"><div className="panel-heading compact"><span className="overline">LIVE TELEMETRY</span><Activity size={15}/></div><div className="telemetry-grid"><div><span>PROCESSING</span><b>{state.processing ? `${state.fps.toFixed(1)} <small>FPS</small>` : '—'}</b></div><div><span>OBJECTS TRACKED</span><b>{state.total_objects}</b></div><div><span>DETECTIONS</span><b>{events.length}</b></div><div><span>MODULES ONLINE</span><b>{Object.values(modules).filter(Boolean).length}<small> / {Object.keys(modules).length || '—'}</small></b></div></div></section>
        <section className="panel telemetry-panel"><div className="panel-heading compact"><span className="overline">OBJECTS IN SESSION</span><span className="count-pill">{state.unique_objects}</span></div><div className="object-inventory">{Object.entries(state.objects_by_class).length ? Object.entries(state.objects_by_class).sort((a, b) => b[1] - a[1]).map(([name, count]) => <span key={name}>{name}<b>{count}</b></span>) : <small>No objects detected yet</small>}</div></section>
        <section className="panel events-panel"><div className="panel-heading compact"><div><span className="overline">SESSION EVENTS</span><h2>Activity</h2></div><span className="count-pill">{events.length}</span></div><div className="events-list">{events.length ? events.slice(0, 5).map((ev, i) => <article className="event-row" key={ev.id ?? i}><span className={`event-marker ${severityClass(ev.severity)}`}/><div><b>{ev.type.replace(/_/g, ' ')}</b><p>{ev.reason}</p></div><time>{new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time></article>) : <div className="events-empty"><CheckCircle2 size={17}/><span>Quiet so far. Events will appear here.</span></div>}</div></section>
      </aside>

      <section className="panel samples-panel"><div className="panel-heading compact"><div><span className="overline">SAMPLE LIBRARY</span><h2>Try a scenario</h2></div><span className="sample-note">TEST FOOTAGE</span></div><div className="sample-list">{samples.map(sample => <button key={sample.file} className={`sample-item ${selectedSample === sample.file ? 'selected' : ''}`} onClick={() => chooseSample(sample.file)}><span className="sample-icon"><FileVideo2 size={17}/></span><span className="sample-copy"><b>{sample.name}</b><small>{sample.kind}</small></span><span className="sample-duration">{sample.duration}</span><ChevronDown size={14} className="sample-chevron"/><span className="sample-play" onClick={e => { e.stopPropagation(); chooseSample(sample.file); void start(sample.file); }} aria-label={`Analyze ${sample.name}`}><Play size={13} fill="currentColor"/></span></button>)}</div><div className="library-foot"><Users size={14}/> Start with Street camera to test people and vehicle detection; the drawn scenario clips may not be recognized by YOLO.</div></section>

      <section className="panel report-panel"><div className="panel-heading compact"><div><span className="overline">AUTOMATIC SUMMARY</span><h2>{report.title}</h2></div>{report.is_demo && <span className="sample-note">SIMULATED</span>}</div><div className="report-body"><p>{report.summary}</p>{report.highlights.length > 0 && <ul>{report.highlights.slice(0, 4).map((h, i) => <li key={i}>{h}</li>)}</ul>}</div></section>
    </div>
    <footer className="footer"><span><b>CIVIS</b> COMPUTER VISION INTELLIGENCE</span><span>Session results update continuously · Review detections before action</span></footer>
  </main>;
}
