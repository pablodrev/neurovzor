import { useNavigate } from 'react-router';
import { House } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Button } from '../../components/ui/Button/Button';
import { Input } from '../../components/ui/Input/Input';
import { Checkbox } from '../../components/ui/Checkbox/Checkbox';
import { Avatar, AvatarFallback } from '../../components/ui/Avatar/Avatar';
import { Badge } from '../../components/ui/Badge/Badge';
import { Card, CardContent } from '../../components/ui/Card/Card';
import { ScrollArea } from '../../components/ui/ScrollArea/ScrollArea';
import Toolbar from '../../components/ui/Toolbar/Toolbar';
import CornerstoneViewer from '../../components/ui/CornerstoneViewer/CornerstoneViewer';
import FileUploader from '../../components/ui/FileUploader/FileUploader';
import './DoctorViewer.scss';

const API_BASE = import.meta.env.VITE_API_BASE ?? '';

const fallbackPatients = [
    {
        id: 'ПТ-2024-1234',
        name: 'Иванов А.В.',
        study: 'Тазобедренный сустав',
        date: '14.03.2025',
        gender: 'Мужчина',
        age: '6 мес.',
    },
    {
        id: 'ПТ-2024-5678',
        name: 'Петров С.В.',
        study: 'Коленный сустав',
        date: '10.12.2024',
        gender: 'Мужчина',
        age: '8 мес.',
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

const fallbackResults = [
    { category: 'lines', parameter: 'Линия Хильгенрейнера', left: '-', right: '-', normal: '-', status: 'success' },
    { category: 'lines', parameter: 'Линия Перкина', left: '-', right: '-', normal: '-', status: 'success' },
    { category: 'lines', parameter: 'Линия Шентона', left: '-', right: '-', normal: '-', status: 'success' },
    { category: 'lines', parameter: 'Линия Кальве', left: '-', right: '-', normal: '-', status: 'success' },

    { category: 'angles', parameter: 'Ацетабулярный угол', left: '24°', right: '18°', normal: '20-25°', status: 'success' },
    { category: 'angles', parameter: 'ШДУ (CCD)', left: '135°', right: '142°', normal: '126-130°', status: 'destructive' },

    { category: 'distances', parameter: 'Расстояние h', left: '9.2 мм', right: '6.5 мм', normal: '>7 мм', status: 'destructive' },
    { category: 'distances', parameter: 'Расстояние d', left: '15.3 мм', right: '14.8 мм', normal: '12-18 мм', status: 'success' },
];

export function DoctorViewer() {
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

    const normalizeLandmarks = (items = []) => items.map((lm) => ({ ...lm, checked: lm.checked ?? true }));

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
                setResults(fallbackResults);
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

    const lines = useMemo(
        () => results.filter((r) => r.category === 'lines'),
        [results]
    );

    const angles = useMemo(
        () => results.filter((r) => r.category === 'angles'),
        [results]
    );

    const distances = useMemo(
        () => results.filter((r) => r.category === 'distances'),
        [results]
    );

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
        <div className="doctor-viewer">
            {/* BEGIN: TopToolbar */}
            <header className="doctor-viewer__header">
                <div className="doctor-viewer__tool-icons" data-purpose="tool-icons">
                    <Toolbar
                        activeTool={activeTool}
                        setActiveTool={setActiveTool}
                    />

                    <div className="doctor-viewer__divider"></div>

                    <Button
                        variant="ghost"
                        size="icon"
                        className="doctor-viewer__tool-btn"
                        onClick={() => navigate('/')}
                        title="Home"
                    >
                        <House className="doctor-viewer__icon" />
                    </Button>
                </div>

                <div className="doctor-viewer__patient-info" data-purpose="patient-header-info">
                    <h1 className="doctor-viewer__patient-name">
                        {activePatient?.name ?? 'Пациент не выбран'}
                    </h1>
                    <p className="doctor-viewer__patient-details">
                        {activePatient
                            ? `${activePatient.date ?? '—'} • ${activePatient.gender ?? '—'}, ${activePatient.age ?? '—'}`
                            : 'Выберите пациента в списке слева'}
                    </p>
                </div>

                <div className="doctor-viewer__mode-switch" data-purpose="mode-switch">
                    <div className="doctor-viewer__mode-group">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate('/student')}
                            className="doctor-viewer__mode-btn"
                        >
                            Я СТУДЕНТ
                        </Button>
                        <Button
                            variant="default"
                            size="sm"
                            className="doctor-viewer__mode-btn doctor-viewer__mode-btn--active"
                        >
                            Я ВРАЧ
                        </Button>
                    </div>

                    <Avatar className="doctor-viewer__avatar">
                        <AvatarFallback>В</AvatarFallback>
                    </Avatar>
                </div>
            </header>
            {/* END: TopToolbar */}

            <main className="doctor-viewer__main">
                {/* BEGIN: LeftPanel */}
                <aside className="doctor-viewer__sidebar doctor-viewer__sidebar--left">
                    <div className="doctor-viewer__sidebar-header">
                        <h2 className="doctor-viewer__sidebar-title">Список пациентов</h2>
                        <div className="doctor-viewer__search">
                            <Input
                                placeholder="Поиск"
                                value={search}
                                onChange={(event) => setSearch(event.target.value)}
                                className="doctor-viewer__search-input"
                            />
                            <svg className="doctor-viewer__search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path>
                            </svg>
                        </div>
                    </div>

                    <ScrollArea className="doctor-viewer__patient-list scrollbar-thin" data-purpose="patient-list">
                        {error && (
                            <div className="doctor-viewer__alert" role="alert">
                                {error}
                            </div>
                        )}

                        {loading ? (
                            <div className="doctor-viewer__patient-empty">Загрузка...</div>
                        ) : filteredPatients.length === 0 ? (
                            <div className="doctor-viewer__patient-empty">Пациенты не найдены</div>
                        ) : (
                            filteredPatients.map((patient) => (
                                <div
                                    key={patient.id}
                                    className={`doctor-viewer__patient-item ${patient.id === activePatientId ? 'doctor-viewer__patient-item--active' : ''}`}
                                    onClick={() => setActivePatientId(patient.id)}
                                >
                                    <div className="doctor-viewer__patient-image" />
                                    <div className="doctor-viewer__patient-details">
                                        <div className="doctor-viewer__patient-header">
                                            <h3 className="doctor-viewer__patient-name">{patient.name}</h3>
                                            <span className="doctor-viewer__patient-date">{patient.date}</span>
                                        </div>
                                        <p className="doctor-viewer__patient-id">{patient.id}</p>
                                        <p className="doctor-viewer__patient-study">{patient.study}</p>
                                    </div>
                                </div>
                            ))
                        )}
                    </ScrollArea>
                </aside>
                {/* END: LeftPanel */}

                {/* BEGIN: CentralViewer */}
                <section className="doctor-viewer__viewport" data-purpose="image-viewport">
                    <div className="doctor-viewer__toolbar-container">
                        {/* Группа загрузки файлов */}
                        <div className="doctor-viewer__upload-group">
                            <FileUploader onFiles={handleFilesUploaded} />
                            {files.length > 0 && (
                                <span className="doctor-viewer__file-count">
                                    {files.length} файл(ов) загружено
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="doctor-viewer__image-container">
                        <div className="doctor-viewer__image-wrapper">
                            {files.length > 0 ? (
                                <CornerstoneViewer
                                    files={files}
                                    activeTool={activeTool}
                                />
                            ) : (
                                <div className="doctor-viewer__placeholder">
                                    <p>Загрузите DICOM или изображение для начала работы</p>
                                    <p className="doctor-viewer__placeholder-hint">
                                        Поддерживаются форматы: .dcm, .jpg, .png
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </section>
                {/* END: CentralViewer */}

                {/* BEGIN: RightPanel */}
                <aside className="doctor-viewer__sidebar doctor-viewer__sidebar--right">
                    <ScrollArea className="doctor-viewer__measurements">
                        <h2 className="doctor-viewer__measurements-title">Диагностические линии и измерения</h2>

                        {/* Group: ЛИНИИ */}
                        <div className="doctor-viewer__measurements-group" data-purpose="diagnostic-lines">
                            <h3 className="doctor-viewer__group-title">Линии</h3>
                            <div className="doctor-viewer__lines-list">
                                <div className="doctor-viewer__line-item">
                                    <span className="doctor-viewer__line-color doctor-viewer__line-color--blue"></span>
                                    <span className="doctor-viewer__line-name">Линия Хильгенрейнера</span>
                                    <Badge variant="outline" className="doctor-viewer__line-check">
                                        <svg className="doctor-viewer__check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3"></path>
                                        </svg>
                                    </Badge>
                                </div>

                                <div className="doctor-viewer__line-item">
                                    <span className="doctor-viewer__line-color doctor-viewer__line-color--green"></span>
                                    <span className="doctor-viewer__line-name">Линия Перкина</span>
                                    <Badge variant="outline" className="doctor-viewer__line-check">
                                        <svg className="doctor-viewer__check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3"></path>
                                        </svg>
                                    </Badge>
                                </div>

                                <div className="doctor-viewer__line-item">
                                    <span className="doctor-viewer__line-color doctor-viewer__line-color--yellow"></span>
                                    <span className="doctor-viewer__line-name">Линия Шентона</span>
                                    <Badge variant="outline" className="doctor-viewer__line-check">
                                        <svg className="doctor-viewer__check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3"></path>
                                        </svg>
                                    </Badge>
                                </div>

                                <div className="doctor-viewer__line-item">
                                    <span className="doctor-viewer__line-color doctor-viewer__line-color--red"></span>
                                    <span className="doctor-viewer__line-name">Линия Кальве</span>
                                    <Badge variant="outline" className="doctor-viewer__line-check">
                                        <svg className="doctor-viewer__check-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3"></path>
                                        </svg>
                                    </Badge>
                                </div>
                            </div>
                        </div>

                        {/* Group: УГЛЫ */}
                        <div className="doctor-viewer__measurements-group" data-purpose="angles-group">
                            <h3 className="doctor-viewer__group-title">Углы</h3>
                            <div className="doctor-viewer__angles-grid">
                                <Card className="doctor-viewer__angle-card">
                                    <CardContent>
                                        <span className="doctor-viewer__angle-label">Ацетабулярный</span>
                                        <span className="doctor-viewer__angle-value doctor-viewer__angle-value--orange">22.4°</span>
                                    </CardContent>
                                </Card>

                                <Card className="doctor-viewer__angle-card">
                                    <CardContent>
                                        <span className="doctor-viewer__angle-label">ШДУ (CCD)</span>
                                        <span className="doctor-viewer__angle-value">135.2°</span>
                                    </CardContent>
                                </Card>
                            </div>
                        </div>

                        {/* Group: РАССТОЯНИЯ */}
                        <div className="doctor-viewer__measurements-group" data-purpose="distances-group">
                            <h3 className="doctor-viewer__group-title">Расстояния</h3>
                            <div className="doctor-viewer__distances-list">
                                <div className="doctor-viewer__distance-item">
                                    <span className="doctor-viewer__distance-label">Высота (h):</span>
                                    <span className="doctor-viewer__distance-value">8.5 mm</span>
                                </div>

                                <div className="doctor-viewer__distance-item">
                                    <span className="doctor-viewer__distance-label">Латерализация (d):</span>
                                    <span className="doctor-viewer__distance-value">15.3 mm</span>
                                </div>

                                <div className="doctor-viewer__checkbox-item">
                                    <Checkbox id="ossification" />
                                    <label htmlFor="ossification" className="doctor-viewer__checkbox-label">
                                        Ядро окостенения головки
                                    </label>
                                </div>
                            </div>
                        </div>

                        {/* Group: НОРМЫ */}
                        <Card className="doctor-viewer__conclusion">
                            <CardContent>
                                <h4 className="doctor-viewer__conclusion-title">Предварительное заключение</h4>
                                <p className="doctor-viewer__conclusion-text">
                                    "Костных деструктивных изменений не выявлено. Соотношения в тазобедренных суставах сохранены. Показатели соответствуют возрастной норме."
                                </p>
                            </CardContent>
                        </Card>
                    </ScrollArea>

                    <div className="doctor-viewer__actions">
                        <Button variant="default" className="doctor-viewer__report-btn">
                            Сформировать отчет
                        </Button>
                    </div>
                </aside>
                {/* END: RightPanel */}
            </main>

            {/* BEGIN: BottomTable */}
            <footer className="doctor-viewer__footer" data-purpose="results-table">
                <div className="doctor-viewer__table-wrapper">
                    <div className="doctor-viewer__table-header">
                        <h2 className="doctor-viewer__table-title">Результаты измерений</h2>
                        <div className="doctor-viewer__legend">
                            <div className="doctor-viewer__legend-item">
                                <span className="doctor-viewer__legend-color doctor-viewer__legend-color--green"></span>
                                <span className="doctor-viewer__legend-text">Норма</span>
                            </div>
                            <div className="doctor-viewer__legend-item">
                                <span className="doctor-viewer__legend-color doctor-viewer__legend-color--red"></span>
                                <span className="doctor-viewer__legend-text">Патология</span>
                            </div>
                            <div className="doctor-viewer__legend-item">
                                <span className="doctor-viewer__legend-color doctor-viewer__legend-color--yellow"></span>
                                <span className="doctor-viewer__legend-text">Внимание</span>
                            </div>
                        </div>
                    </div>

                    <ScrollArea className="doctor-viewer__table-scroll">
                        <table className="doctor-viewer__table">
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
                                        <td className="doctor-viewer__table-cell" colSpan={5}>
                                            Нет данных для отображения.
                                        </td>
                                    </tr>
                                ) : (
                                    results.map((row) => {
                                        const status = row.status || 'success';

                                        return (
                                            <tr key={row.parameter}>
                                                <td className="doctor-viewer__table-cell">{row.parameter}</td>
                                                <td>{row.left}</td>
                                                <td>{row.right}</td>
                                                <td className="doctor-viewer__table-muted">{row.normal}</td>
                                                <td>
                                                    <div className={`doctor-viewer__status doctor-viewer__status--${status}`}>
                                                        <Checkbox checked={status === 'success'} className="doctor-viewer__status-checkbox" />
                                                        <span>{status === 'success' ? 'НОРМА' : status.toUpperCase()}</span>
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
            </footer>
            {/* END: BottomTable */}
        </div>
    );
}