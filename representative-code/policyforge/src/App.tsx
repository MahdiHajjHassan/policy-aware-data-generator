import React, {useEffect, useMemo, useState} from 'react';
import {api, ErrorNotice, Icon, SourceLink, ThemeToggle} from './ui';

type Config = {schema: Record<string, Record<string, any>>; contract: any};
const pretty = (value: any) => JSON.stringify(value, null, 2);
const clone = (value: any) => JSON.parse(JSON.stringify(value));

export default function App() {
  const [state, setState] = useState<any>(null);
  const [config, setConfig] = useState<Config | null>(null);
  const [view, setView] = useState('workspace');
  const [editor, setEditor] = useState('fields');
  const [table, setTable] = useState('employees');
  const [field, setField] = useState('annual_salary');
  const [fieldText, setFieldText] = useState('');
  const [schemaText, setSchemaText] = useState('');
  const [contractText, setContractText] = useState('');
  const [country, setCountry] = useState('Aster');
  const [resultTable, setResultTable] = useState('employees');
  const [resultTab, setResultTab] = useState('data');
  const [query, setQuery] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  function loadConfig(next: Config) {
    setConfig(clone(next));
    setSchemaText(pretty(next.schema));
    setContractText(pretty(next.contract));
    setFieldText(pretty(next.schema[table]?.[field] || {}));
  }
  async function refresh(replaceConfig = false) {
    const next = await api.state();
    setState(next);
    if (replaceConfig || !config) loadConfig(next.config);
    if (next.package && !next.package.partitions[country]) setCountry(Object.keys(next.package.partitions)[0]);
    if (next.package && !next.package.contract.tables.includes(resultTable)) setResultTable(next.package.contract.tables[0]);
    return next;
  }
  useEffect(() => {refresh(true).catch(e => setError(e.message));}, []);

  const fieldPending = config && fieldText !== pretty(config.schema[table]?.[field] || {});
  const pending = !!config && (pretty(config) !== pretty(state?.config) || schemaText !== pretty(config.schema) || contractText !== pretty(config.contract) || fieldPending);
  const preview = state?.compilation;
  const pkg = state?.package;
  const activePart = pkg?.partitions[country];
  const rows = activePart?.tables[resultTable] || [];
  const filtered = useMemo(() => rows.filter((r: any) => Object.values(r).some(v => String(v).toLowerCase().includes(query.toLowerCase()))), [rows, query]);

  function updateContract(patch: any) {
    if (!config) return;
    const next = {...config, contract: {...config.contract, ...patch}};
    setConfig(next); setContractText(pretty(next.contract));
  }
  function pickField(nextTable: string, nextField: string) {
    if (!config) return;
    try {
      const next = effectiveConfig();
      if (!next.schema[nextTable]?.[nextField]) throw new Error('This field changed in the schema JSON. Save the schema before opening another field.');
      setConfig(next); setSchemaText(pretty(next.schema)); setContractText(pretty(next.contract));
      setTable(nextTable); setField(nextField); setFieldText(pretty(next.schema[nextTable][nextField]));
      setError('');
    } catch (e: any) {setError(e.message);}
  }
  function effectiveConfig() {
    if (!config) throw new Error('The configuration is still loading.');
    const next = clone(config);
    try {
      if (schemaText !== pretty(config.schema)) next.schema = JSON.parse(schemaText);
      if (contractText !== pretty(config.contract)) next.contract = JSON.parse(contractText);
      if (fieldPending && next.schema[table]?.[field]) next.schema[table][field] = JSON.parse(fieldText);
    } catch (e) {throw new Error('The metadata contains invalid JSON. Check commas and quotes, then save again.');}
    return next;
  }
  async function run(name: string, payload: any = {}, save = false) {
    setBusy(name); setError(''); setNotice('');
    try {
      if (save && pending) {
        const next = effectiveConfig();
        await api.action('save_config', next);
        loadConfig(next);
      }
      const result = await api.action(name, payload);
      await refresh(name === 'reset_config' || name === 'save_config');
      setNotice(result.message || (name === 'compile' ? 'Field policy compiled from the saved metadata.' : 'Action complete.'));
      if (name === 'generate') {setResultTab('data'); setView('workspace');}
      return result;
    } catch (e: any) {
      setError(e.message);
      await refresh();
      return null;
    } finally {setBusy('');}
  }
  async function save() {
    try {await run('save_config', effectiveConfig());} catch (e: any) {setError(e.message);}
  }
  async function selectRecipient(id: string) {
    const result = await run('select_recipient', {recipient_id: id});
    if (result) setNotice('Recipient selected. Review its country scope before generating.');
  }
  async function exportPackage(format: string) {
    const result = await run('export', {package_id: pkg.package_id, format, country, table: resultTable});
    if (!result) return;
    const bytes = result.content_base64 ? Uint8Array.from(atob(result.content_base64), c => c.charCodeAt(0)) : result.content;
    const href = URL.createObjectURL(new Blob([bytes], {type: result.mime}));
    const a = document.createElement('a'); a.href = href; a.download = result.filename; a.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
    setNotice(`${format.toUpperCase()} downloaded after release validation.`);
  }
  function applyField() {
    try {
      const metadata = JSON.parse(fieldText);
      if (!config) return;
      const next = clone(config); next.schema[table][field] = metadata;
      setConfig(next); setSchemaText(pretty(next.schema)); setFieldText(pretty(metadata));
      setNotice('Field metadata applied to the draft. Save or generate to validate it.'); setError('');
    } catch {setError('Field metadata contains invalid JSON. Check the syntax before applying.');}
  }

  if (!state || !config) return <div className="loading-studio"><Icon name="Layers" size={30}/><h1>PolicyForge</h1><p>Loading dataset workspace…</p><ErrorNotice error={error}/><div className="loading-lines" aria-hidden="true"/></div>;
  const meta = config.schema[table]?.[field] || {};
  const fieldAccess = preview?.field_matrix?.filter((f: any) => f.table === table && f.field === field) || [];
  const canDownload = pkg && !state.package_stale && !pending;

  return <div className="studio">
    <header className="app-header">
      <a className="wordmark" href="/" aria-label="PolicyForge workspace"><Icon name="Layers" size={23}/><strong>PolicyForge</strong><span>Schema studio</span></a>
      <div className="header-tools"><span className="local-label"><span/>Local workspace</span><SourceLink/><ThemeToggle/></div>
    </header>
    <nav className="primary-nav" aria-label="Workspace views">
      {[['workspace', 'Dataset workspace', 'Database'], ['policies', 'Access policies', 'ShieldCheck'], ['audit', 'Run history', 'Clock']].map(([id, label, icon]) => <button key={id} className={view === id ? 'active' : ''} onClick={() => setView(id)} aria-current={view === id ? 'page' : undefined}><Icon name={icon} size={16}/>{label}</button>)}
      <span className="policy-version">Policy {state.policy_version.replace('local-product-', 'v')}</span>
    </nav>
    <div className="studio-body">
      <aside className="policy-rail">
        <div className="rail-section recipient-section"><h2>Recipient</h2><p>Choose an access profile.</p><div className="recipient-list">
          {state.recipients.map((r: any) => <button key={r.id} className={`recipient ${state.recipient.id === r.id ? 'selected' : ''}`} onClick={() => selectRecipient(r.id)} disabled={!!busy} aria-pressed={state.recipient.id === r.id}><span className="recipient-mark">{r.team.slice(0, 1).toUpperCase()}</span><span><strong>{r.label}</strong><small>{r.team} team</small></span>{state.recipient.id === r.id && <Icon name="Check" size={15}/>}</button>)}
        </div><div className="profile-binding"><span>Assigned role</span><code>{state.recipient.roles[0]}</code><span className="profile-note"><Icon name="ShieldCheck" size={13}/>Bound to trusted profile</span></div></div>
        <div className="rail-section"><h2>Generation scope</h2><div className="country-options"><span className="control-label">Country partitions</span>{state.countries.map((c: string) => <label key={c} className={`country-check ${!state.country_scope.includes(c) ? 'restricted' : ''}`}><input type="checkbox" checked={config.contract.countries.includes(c)} onChange={e => updateContract({countries: e.target.checked ? [...config.contract.countries, c] : config.contract.countries.filter((v: string) => v !== c)})}/><span>{c}</span><small>{state.country_scope.includes(c) ? 'In scope' : 'Restricted'}</small></label>)}</div>
          <label className="rows-control">Rows per table / country<input aria-label="Rows per country" type="number" min={1} max={500} value={config.contract.rows} onChange={e => updateContract({rows: Number(e.target.value)})}/><span className="control-hint">1–500 records per partition</span></label>
          <label>Generation seed<input aria-label="Generation seed" value={config.contract.seed} maxLength={80} onChange={e => updateContract({seed: e.target.value})}/><span className="control-hint">The same inputs reproduce the output.</span></label>
          <button className="primary generate-button" disabled={!!busy} onClick={() => run('generate', {}, true)}><Icon name={busy === 'generate' ? 'RefreshCw' : 'Play'} size={17}/>{busy === 'generate' ? 'Generating…' : 'Generate dataset'}</button>
          <button className="compile-button" disabled={!!busy} onClick={() => run('compile', {}, true)}><Icon name="GitBranch" size={15}/>Compile policy</button>
        </div>
        <div className="rail-section policy-layers"><h2>Release policy</h2><p>All layers must allow a field.</p>{[['Database','Dataset','workforce_reference'], ['Building2','Team',state.recipient.team], ['Users','Role',state.recipient.roles[0]], ['ShieldCheck','Country',config.contract.countries.join(', ') || 'Choose a country']].map(([icon,label,value]) => <div className="policy-layer" key={label}><Icon name={icon} size={15}/><span><small>{label}</small><strong>{value}</strong></span><Icon name={label === 'Country' && (!config.contract.countries.length || config.contract.countries.some((c:string) => !state.country_scope.includes(c))) ? 'X' : 'Check'} size={13}/></div>)}<button className="text-button" onClick={() => setView('policies')}>Inspect field access<Icon name="ArrowRight" size={14}/></button></div>
        <div className="rail-foot"><Icon name="Database" size={14}/><span>Synthetic reference records</span></div>
      </aside>
      <main className="main-workspace">
        <div className="workspace-heading"><div><div className="dataset-path"><Icon name="Database" size={14}/>workforce_reference<Icon name="ChevronRight" size={13}/><span>{config.contract.version}</span></div><h1>{view === 'workspace' ? config.contract.name : view === 'policies' ? 'Access policies' : 'Run history'}</h1></div><div className="heading-actions">{view === 'workspace' && <><span className={`save-state ${pending ? 'changed' : ''}`}><span/>{pending ? 'Unsaved changes' : 'Saved locally'}</span><button onClick={save} disabled={!!busy || !pending}><Icon name="Check" size={15}/>Save contract</button></>}</div></div>
        <ErrorNotice error={error}/>
        {notice && <div className="action-notice" role="status"><Icon name="CheckCircle2" size={15}/><span>{notice}</span><button className="icon-button" aria-label="Dismiss notice" onClick={() => setNotice('')}><Icon name="X" size={14}/></button></div>}
        {view === 'workspace' && <>
          <section className="schema-workspace" aria-label="Schema and contract editor">
            <div className="section-toolbar"><div className="editor-tabs" role="tablist" aria-label="Metadata editor">{[['fields','Schema fields'],['schema','Schema JSON'],['contract','Contract JSON']].map(([id,label]) => <button key={id} role="tab" aria-selected={editor === id} className={editor === id ? 'active' : ''} onClick={() => setEditor(id)}>{label}</button>)}</div><span className="schema-file"><Icon name="FileText" size={13}/>{editor === 'contract' ? 'contract.json' : 'schema.json'}</span></div>
            {editor === 'fields' ? <div className="field-studio">
              <div className="field-list"><div className="table-picker">{Object.keys(config.schema).map(t => <button key={t} className={table === t ? 'active' : ''} onClick={() => pickField(t, Object.keys(config.schema[t])[0])}><Icon name="Database" size={13}/>{t}<span>{Object.keys(config.schema[t]).length}</span></button>)}</div><div className="field-column-head"><span>Field</span><span>Classification</span></div><div className="field-scroll">{Object.entries(config.schema[table]).map(([name,m]: [string,any]) => <button key={name} className={`field-row ${field === name ? 'active' : ''}`} onClick={() => pickField(table,name)}><span><Icon name={m.category === 'structural' ? 'GitBranch' : 'Circle'} size={12}/><code>{name}</code>{m.required && <small title="Required">*</small>}</span><small className={`category category-${m.category}`}>{m.category}</small></button>)}</div><div className="field-list-foot"><span>* Required by contract</span><span>{Object.keys(config.schema[table]).length} fields</span></div></div>
              <div className="field-inspector"><div className="inspector-title"><div><h2>{field}</h2><span>{table} / {meta.type}</span></div><span className={`category category-${meta.category}`}>{meta.category}</span></div><label className="code-label" htmlFor="field-metadata">Field metadata<textarea id="field-metadata" className="code-editor field-code" spellCheck={false} value={fieldText} onChange={e => setFieldText(e.target.value)} aria-label="Field metadata JSON"/></label><div className="inspector-footer"><div className="field-permissions">{fieldAccess.length ? fieldAccess.map((f:any) => <span className={f.allowed ? 'allowed' : 'excluded'} key={f.country}><Icon name={f.allowed ? 'Check' : 'X'} size={12}/>{f.country}: {f.allowed ? 'allowed' : 'excluded'}</span>) : <span>Save and compile to inspect access.</span>}</div><button className="apply-field" onClick={applyField} disabled={!fieldPending || !!busy}>Apply field<Icon name="ArrowRight" size={13}/></button></div></div>
            </div> : <div className="full-code"><div className="code-description"><span>{editor === 'schema' ? 'Edit typed fields, classifications and generator rules. Unknown or unclassified fields stop the release.' : 'Edit the dataset name, version, table selection, row count, countries and seed.'}</span><button className="text-button" disabled={!!busy} onClick={() => run('reset_config')}>Restore defaults<Icon name="RefreshCw" size={13}/></button></div><textarea className="code-editor" aria-label={editor === 'schema' ? 'Schema JSON' : 'Contract JSON'} spellCheck={false} value={editor === 'schema' ? schemaText : contractText} onChange={e => editor === 'schema' ? setSchemaText(e.target.value) : setContractText(e.target.value)}/></div>}
          </section>
          <section className="dataset-output" aria-label="Generated dataset">
            <div className="output-heading"><div className="output-title"><h2>Generated dataset</h2>{pkg && <span className={`release-status ${state.package_stale || pending ? 'stale' : ''}`}><Icon name={state.package_stale || pending ? 'Clock' : 'ShieldCheck'} size={13}/>{state.package_stale || pending ? 'Regeneration needed' : 'Validated'}</span>}</div><div className="download-actions"><button disabled={!canDownload || !!busy} onClick={() => exportPackage('json')}>JSON</button><button disabled={!canDownload || !!busy} onClick={() => exportPackage('csv')}>CSV</button><button className="package-download" disabled={!canDownload || !!busy} onClick={() => exportPackage('zip')}><Icon name="Download" size={14}/>Download package</button></div></div>
            {pkg ? <><div className="output-toolbar"><div className="result-tabs" role="tablist" aria-label="Output views">{[['data','Data preview'],['access','Field access'],['manifest','Manifest']].map(([id,label]) => <button role="tab" aria-selected={resultTab === id} className={resultTab === id ? 'active' : ''} key={id} onClick={() => setResultTab(id)}>{label}</button>)}</div><div className="partition-selectors"><select aria-label="Result country" value={country} onChange={e => {setCountry(e.target.value); setQuery('');}}>{Object.keys(pkg.partitions).map(c => <option key={c}>{c}</option>)}</select><select aria-label="Result table" value={resultTable} onChange={e => {setResultTable(e.target.value); setQuery('');}}>{pkg.contract.tables.map((t:string) => <option key={t}>{t}</option>)}</select></div></div>
              {resultTab === 'data' && <><div className="result-summary"><span><strong>{rows.length}</strong> records<span className="divider">/</span>{activePart?.fields[resultTable]?.length} permitted fields<span className="divider">/</span><span className="omitted-count">{activePart?.omitted_fields[resultTable]?.length || 0} excluded</span></span><label className="table-search"><Icon name="Search" size={14}/><input aria-label="Search dataset" placeholder="Search records" value={query} onChange={e => setQuery(e.target.value)}/></label></div><div className="dataset-table-scroll"><table className="dataset-table"><thead><tr><th className="row-number">#</th>{activePart?.fields[resultTable]?.map((f:string) => <th key={f}><code>{f}</code></th>)}</tr></thead><tbody>{filtered.slice(0, 100).map((r:any,i:number) => <tr key={i}><td className="row-number">{i+1}</td>{activePart.fields[resultTable].map((f:string) => <td className={f.endsWith('_id') ? 'identifier-cell' : typeof r[f] === 'number' ? 'number-cell' : ''} key={f}>{typeof r[f] === 'boolean' ? String(r[f]) : r[f]}</td>)}</tr>)}{!filtered.length && <tr><td colSpan={20} className="empty-search">No records match this search. Try another value.</td></tr>}</tbody></table></div><div className="table-foot"><span>{filtered.length > 100 ? 'Showing the first 100 of ' + filtered.length : filtered.length} records{query && ' matching search'}</span><span className="package-id"><Icon name="Package" size={13}/>{pkg.package_id}</span><button className="text-button" disabled={!canDownload || !!busy} onClick={() => run('validate', {package_id: pkg.package_id})}><Icon name="ShieldCheck" size={13}/>Run validation</button></div></>}
              {resultTab === 'access' && <AccessTable matrix={preview.field_matrix.filter((f:any) => f.country === country && f.table === resultTable)} denied={preview.error} stale={state.package_stale || pending}/>}
              {resultTab === 'manifest' && <div className="manifest-layout"><div><h3>Release checks</h3>{pkg.manifest.validation.checks.map((c:string) => <p className="validation-check" key={c}><Icon name="CheckCircle2" size={15}/>{c}</p>)}<p className="manifest-note">Validated against the generated contract. Downloads recheck the saved metadata and recipient.</p></div><pre>{pretty(pkg.manifest)}</pre></div>}
            </> : <div className="empty-output"><Icon name="Database" size={30}/><h3>No package for this recipient</h3><p>Choose its permitted countries, then generate a dataset. The package will contain only fields allowed by every policy layer.</p><button onClick={() => run('generate', {}, true)} disabled={!!busy}>Generate dataset<Icon name="ArrowRight" size={14}/></button></div>}
          </section>
        </>}
        {view === 'policies' && <div className="policy-view"><p className="view-intro">The compiler intersects dataset, team, assigned role and country rules. Optional denied fields are omitted. A denied required field stops the entire release.</p><div className="policy-legend"><span className="allowed"><Icon name="Check" size={14}/>Allowed</span><span className="excluded"><Icon name="X" size={14}/>Excluded</span><span>{state.recipient.label} / {config.contract.countries.join(', ')}</span><button onClick={() => run('compile', {}, true)} disabled={!!busy}>Compile current policy</button></div><AccessTable matrix={preview.field_matrix} denied={preview.error} stale={pending}/><details className="policy-source"><summary><Icon name="Code2" size={16}/>Trusted policy source<Icon name="ChevronDown" size={15}/></summary><pre>{pretty(state.policy)}</pre></details></div>}
        {view === 'audit' && <div className="audit-view"><div className="audit-intro"><p>Persisted generation, compilation, validation and download decisions for {state.recipient.label}.</p><span>{state.audit.length} events</span></div><div className="audit-table-scroll"><table><thead><tr><th>Time</th><th>Action</th><th>Decision</th><th>Details</th></tr></thead><tbody>{[...state.audit].reverse().map((a:any,i:number) => <tr key={i}><td className="audit-time">{new Date(a.time).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'})}<small>{new Date(a.time).toLocaleDateString()}</small></td><td><code>{a.action}</code></td><td><span className={`decision-label ${a.status}`}><Icon name={a.status === 'allowed' ? 'Check' : 'X'} size={13}/>{a.status}</span></td><td>{a.detail}{a.package_id && <small className="audit-package">{a.package_id}</small>}</td></tr>)}</tbody></table></div></div>}
        <footer className="workspace-footer"><span><Icon name="ShieldCheck" size={13}/>Policy enforced before generation and download</span><span>PolicyForge · Local product</span></footer>
      </main>
    </div>
  </div>;
}

function AccessTable({matrix, denied, stale}: {matrix: any[]; denied?: string; stale?: boolean}) {
  if (denied) return <div className="policy-denial"><Icon name="ShieldCheck" size={25}/><div><h3>Release blocked</h3><p>{denied}</p></div></div>;
  return <div className="access-matrix">{stale && <p className="matrix-warning"><Icon name="Clock" size={14}/>This matrix uses the saved metadata. Save and compile your changes to update it.</p>}<div className="access-table-scroll"><table><thead><tr><th>Field</th><th>Classification</th><th>Country</th><th>Access</th><th>Policy decision</th></tr></thead><tbody>{matrix.map((f:any,i:number) => <tr key={i}><td><span className="table-prefix">{f.table}.</span><code>{f.field}</code>{f.required && <small className="required-star">*</small>}</td><td><span className={`category category-${f.category}`}>{f.category}</span></td><td>{f.country}</td><td><span className={f.allowed ? 'allowed' : 'excluded'}><Icon name={f.allowed ? 'Check' : 'X'} size={13}/>{f.allowed ? 'Allowed' : 'Excluded'}</span></td><td className="policy-reason">{f.reason}</td></tr>)}</tbody></table></div></div>;
}
