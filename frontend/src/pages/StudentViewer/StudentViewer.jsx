import { useNavigate } from 'react-router';
import { useEffect, useMemo, useState } from 'react';
import { House } from 'lucide-react';
import { Button } from '../../components/ui/Button/Button';
import { Checkbox } from '../../components/ui/Checkbox/Checkbox';
import { Input } from '../../components/ui/Input/Input';
import { Avatar, AvatarFallback } from '../../components/ui/Avatar/Avatar';
import { ScrollArea } from '../../components/ui/ScrollArea/ScrollArea';
import Toolbar from '../../components/ui/Toolbar/Toolbar';
import CornerstoneViewer from '../../components/ui/CornerstoneViewer/CornerstoneViewer';
import FileUploader from '../../components/ui/FileUploader/FileUploader';
import './StudentViewer.scss';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

const fallbackPatients = [
    {
        id: 'ПТ-2024-1234',
        name: 'Иванов А.В.',
        study: 'Тазобедренный сустав',
        date: '14.03.2025',
    },
    {
        id: 'ПТ-2024-5678',
        name: 'Петров С.В.',
        study: 'Коленный сустав',
        date: '10.12.2024',
    },
];

const fallbackLandmarks = [
    { id: 'pelvis-y-cartilage-left', category: 'pelvis', name: 'Левый Y-образный хрящ', checked: true },
    { id: 'pelvis-y-cartilage-right', category: 'pelvis', name: 'Правый Y-образный хрящ', checked: true },
    { id: 'pelvis-acetabular-roof', category: 'pelvis', name: 'Верхний край крыши вертл. впадины', checked: true },
    { id: 'pelvis-acetabular-roof-external', category: 'pelvis', name: 'Наружный край крыши вертл. впадины', checked: true },
    { id: 'pelvis-acetabular-fossa', category: 'pelvis', name: 'Дно вертлужной впадины', checked: true },
    { id: 'pelvis-obturator-foramen', category: 'pelvis', name: 'Верхний край запирательного отв.', checked: true },
    { id: 'femur-head', category: 'femur', name: 'Головка бедренной кости', checked: true },
    { id: 'femur-neck', category: 'femur', name: 'Шейка бедренной кости', checked: true },
    { id: 'femur-shaft', category: 'femur', name: 'Диафиз бедренной кости', checked: true },
    { id: 'femur-metaphysis', category: 'femur', name: 'Метафизарная пластинка', checked: true },
    { id: 'femur-ossification', category: 'femur', name: 'Ядро окостенения головки', checked: true },
];

export function StudentViewer() {
    const navigate = useNavigate();
    const [activeTool, setActiveTool] = useState('Pan');
    const [files, setFiles] = useState([]);
    const [search, setSearch] = useState('');
    const [patients, setPatients] = useState([]);
    const [activePatientId, setActivePatientId] = useState(null);
    const [landmarks, setLandmarks] = useState([]);
    const [results, setResults] = useState([]);
    const [confidence, setConfidence] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const apiFetch = async (path, options = {}) => {
        const url = `${API_BASE}${path}`;
        const res = await fetch(url, {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });

        if (!res.ok) {
            throw new Error(`API request failed (${res.status}) ${url}`);
        }

        return res.json();
    };

    const normalizeLandmarks = (items = []) =>
        items.map((lm) => ({ ...lm, checked: lm.checked ?? true }));

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            setError(null);

            try {
                const patientsData = await apiFetch('/api/patients');
                setPatients(patientsData);
                setActivePatientId(patientsData[0]?.id ?? null);
            } catch (err) {
                console.error('Failed to load patients', err);
                setError('Не удалось загрузить список пациентов');
                setPatients(fallbackPatients);
                setActivePatientId(fallbackPatients[0]?.id ?? null);
            } finally {
                setLoading(false);
            }
        };

        load();
    }, []);

    useEffect(() => {
        if (!activePatientId) return;

        const loadPatientData = async () => {
            try {
                const [landmarksData, resultsData, confidenceData] = await Promise.all([
                    apiFetch(`/api/patients/${activePatientId}/landmarks`),
                    apiFetch(`/api/patients/${activePatientId}/results`),
                    apiFetch(`/api/patients/${activePatientId}/confidence`),
                ]);

                setLandmarks(normalizeLandmarks(landmarksData));
                setResults(resultsData);
                setConfidence(confidenceData?.value ?? null);
            } catch (err) {
                console.error('Failed to load patient data', err);
                setLandmarks(normalizeLandmarks(fallbackLandmarks));
                setResults([]);
                setConfidence(null);
            }
        };

        loadPatientData();
    }, [activePatientId]);

    const activePatient = useMemo(
        () => patients.find((p) => p.id === activePatientId) ?? null,
        [patients, activePatientId]
    );

    const filteredPatients = useMemo(() => {
        const term = search.trim().toLowerCase();
        if (!term) return patients;

        return patients.filter((patient) => {
            return (
                patient.name.toLowerCase().includes(term) ||
                patient.id.toLowerCase().includes(term) ||
                patient.study.toLowerCase().includes(term)
            );
        });
    }, [patients, search]);

    const toggleLandmark = async (id, checked) => {
        const nextValue = checked ?? true;

        setLandmarks((prev) =>
            prev.map((lm) => (lm.id === id ? { ...lm, checked: nextValue } : lm))
        );

        if (!activePatientId) return;

        try {
            await apiFetch(`/api/patients/${activePatientId}/landmarks/${id}`, {
                method: 'PUT',
                body: JSON.stringify({ checked: nextValue }),
            });
        } catch (err) {
            console.error('Failed to update landmark', err);
        }
    };

    const handleFilesUploaded = (uploadedFiles) => {
        setFiles(uploadedFiles);
        console.log('Загружено файлов:', uploadedFiles.length);
    };

    return (
        <div className="student-viewer">
            {/* TOP BAR */}
            <header className="student-viewer__header">
                <div className="student-viewer__tool-icons" data-purpose="tool-icons">
                    <Toolbar
                        activeTool={activeTool}
                        setActiveTool={setActiveTool}
                    />

                    <div className="student-viewer__divider"></div>

                    <Button
                        variant="ghost"
                        size="icon"
                        className="student-viewer__tool-btn"
                        onClick={() => navigate('/')}
                        title="Home"
                    >
                        <House className="student-viewer__icon" />
                    </Button>
                </div>

                <div className="student-viewer__patient-info" data-purpose="patient-header-info">
                    <h1 className="student-viewer__patient-name">{activePatient?.name ?? 'Пациент не выбран'}</h1>
                    <p className="student-viewer__patient-details">
                        {activePatient ? `${activePatient.date ?? '—'} • ${activePatient.gender ?? '—'}, ${activePatient.age ?? '—'}` : 'Выберите пациента слева'}
                    </p>
                </div>

                <div className="student-viewer__mode-section" data-purpose="mode-switch">
                    <div className="student-viewer__mode-group">
                        <Button
                            variant="default"
                            size="sm"
                            className="student-viewer__mode-btn student-viewer__mode-btn--active"
                        >
                            Я СТУДЕНТ
                        </Button>
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate('/doctor')}
                            className="student-viewer__mode-btn"
                        >
                            Я ВРАЧ
                        </Button>
                    </div>

                    <Avatar className="student-viewer__avatar">
                        <AvatarFallback>С</AvatarFallback>
                    </Avatar>
                </div>
            </header>

            <div className="student-viewer__main">
                {/* LEFT PANEL: PATIENT LIST */}
                <aside className="student-viewer__sidebar student-viewer__sidebar--left">
                    <div className="student-viewer__sidebar-header">
                        <h2 className="student-viewer__sidebar-title">Список пациентов</h2>
                        <div className="student-viewer__search">
                            <Input
                                placeholder="Поиск"
                                value={search}
                                onChange={(event) => setSearch(event.target.value)}
                                className="student-viewer__search-input"
                            />
                            <svg className="student-viewer__search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path>
                            </svg>
                        </div>
                    </div>

                    {error && (
                        <div className="student-viewer__alert" role="alert">
                            {error}
                        </div>
                    )}

                    <ScrollArea className="student-viewer__patient-list">
                        {loading ? (
                            <div className="student-viewer__patient-empty">Загрузка...</div>
                        ) : filteredPatients.length === 0 ? (
                            <div className="student-viewer__patient-empty">Пациенты не найдены</div>
                        ) : (
                            filteredPatients.map((patient) => (
                                <div
                                    key={patient.id}
                                    className={`student-viewer__patient-item ${patient.id === activePatientId ? 'student-viewer__patient-item--active' : ''}`}
                                    onClick={() => setActivePatientId(patient.id)}
                                >
                                    <div className="student-viewer__patient-image" />
                                    <div className="student-viewer__patient-details">
                                        <p className="student-viewer__patient-name">{patient.name}</p>
                                        <p className="student-viewer__patient-id">{patient.id}</p>
                                        <p className="student-viewer__patient-study">{patient.study}</p>
                                        <p className="student-viewer__patient-date">{patient.date}</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </ScrollArea>
                </aside>

                {/* CENTRAL VIEWER */}
                <main className="student-viewer__viewport">
                    <div className="student-viewer__toolbar-container">
                        {/* Группа загрузки файлов */}
                        <div className="student-viewer__upload-group">
                            <FileUploader onFiles={handleFilesUploaded} />
                            {files.length > 0 && (
                                <span className="student-viewer__file-count">
                                    {files.length} файл(ов) загружено
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="student-viewer__image-container">
                        <div className="student-viewer__image-wrapper">
                            {files.length > 0 ? (
                                <CornerstoneViewer
                                    files={files}
                                    activeTool={activeTool}
                                />
                            ) : (
                                <div className="student-viewer__placeholder">
                                    <p>Загрузите DICOM или изображение для начала работы</p>
                                    <p className="student-viewer__placeholder-hint">
                                        Поддерживаются форматы: .dcm, .jpg, .png
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* BOTTOM TABLE: RESULTS */}
                    <div className="student-viewer__results">
                        <div className="student-viewer__results-header">
                            <h3 className="student-viewer__results-title">Результаты измерений</h3>
                            <div className="student-viewer__legend">
                                <div className="student-viewer__legend-item">
                                    <div className="student-viewer__legend-color student-viewer__legend-color--success"></div>
                                    <span className="student-viewer__legend-text">Норма</span>
                                </div>
                                <div className="student-viewer__legend-item">
                                    <div className="student-viewer__legend-color student-viewer__legend-color--warning"></div>
                                    <span className="student-viewer__legend-text">Погранично</span>
                                </div>
                            </div>
                        </div>

                        <ScrollArea className="student-viewer__table-container scrollbar-thin">
                            <table className="student-viewer__table">
                                <thead>
                                    <tr>
                                        <th>Параметр</th>
                                        <th>Левый</th>
                                        <th>Правый</th>
                                        <th>Норма</th>
                                        <th>Статус</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.length === 0 ? (
                                        <tr>
                                            <td className="student-viewer__table-cell" colSpan={5}>
                                                Нет данных измерений.
                                            </td>
                                        </tr>
                                    ) : (
                                        results.map((row) => {
                                            const status = row.status || 'success';
                                            return (
                                                <tr key={row.parameter}>
                                                    <td className="student-viewer__table-cell">{row.parameter}</td>
                                                    <td>{row.left}</td>
                                                    <td>{row.right}</td>
                                                    <td className="student-viewer__table-muted">{row.normal}</td>
                                                    <td>
                                                        <div className={`student-viewer__status student-viewer__status--${status}`}>
                                                            <Checkbox checked={status === 'success'} className="student-viewer__status-checkbox" />
                                                            <span>{status === 'success' ? 'НОРМА' : status?.toUpperCase() || '—'}</span>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })
                                    )}
                                </tbody>
                            </table>
                        </ScrollArea>
                    </div>
                </main>

                {/* RIGHT PANEL: DETECTION INFO */}
                <aside className="student-viewer__sidebar student-viewer__sidebar--right">
                    <div className="student-viewer__detection-header">
                        <h2 className="student-viewer__detection-title">Детекция анатомических ориентиров</h2>
                    </div>

                    <ScrollArea className="student-viewer__detection-content">
                        {/* Section: Pelvis */}
                        <section className="student-viewer__section">
                            <div className="student-viewer__section-header">
                                <div className="student-viewer__section-indicator"></div>
                                <h3 className="student-viewer__section-title">ТАЗ</h3>
                            </div>

                            <ul className="student-viewer__landmark-list">
                                {landmarks
                                    .filter((lm) => lm.category === 'pelvis')
                                    .map((landmark) => (
                                        <li key={landmark.id} className="student-viewer__landmark-item">
                                            <div className="student-viewer__landmark-info">
                                                <div
                                                    className={`student-viewer__landmark-dot student-viewer__landmark-dot--${landmark.category}`}
                                                ></div>
                                                <span className="student-viewer__landmark-name">{landmark.name}</span>
                                            </div>
                                            <Checkbox
                                                checked={landmark.checked}
                                                onCheckedChange={(value) => toggleLandmark(landmark.id, value)}
                                            />
                                        </li>
                                    ))}
                            </ul>
                        </section>

                        {/* Section: Femur */}
                        <section className="student-viewer__section">
                            <div className="student-viewer__section-header">
                                <div className="student-viewer__section-indicator"></div>
                                <h3 className="student-viewer__section-title">БЕДРЕННАЯ КОСТЬ</h3>
                            </div>

                            <ul className="student-viewer__landmark-list">
                                {landmarks
                                    .filter((lm) => lm.category === 'femur')
                                    .map((landmark) => (
                                        <li key={landmark.id} className="student-viewer__landmark-item">
                                            <div className="student-viewer__landmark-info">
                                                <div
                                                    className={`student-viewer__landmark-dot student-viewer__landmark-dot--${landmark.category}`}
                                                ></div>
                                                <span className="student-viewer__landmark-name">{landmark.name}</span>
                                            </div>
                                            <Checkbox
                                                checked={landmark.checked}
                                                onCheckedChange={(value) => toggleLandmark(landmark.id, value)}
                                            />
                                        </li>
                                    ))}
                            </ul>
                        </section>
                    </ScrollArea>

                    {/* Footer: System status */}
                    <div className="student-viewer__footer">
                        <p className="student-viewer__confidence">AI Confidence: {confidence != null ? `${confidence}%` : '—'}</p>
                        <Button variant="ghost" className="student-viewer__report-btn">
                            Сформировать отчет
                        </Button>
                    </div>
                </aside>
            </div>
        </div>
    );
}