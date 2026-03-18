import { useNavigate, useSearchParams } from 'react-router';
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
import api from '../../services/api.js';
import './DoctorViewer.scss';

const fallbackPatients = [
    {
        id: 'ПТ-2024-1234',
        name: 'Иванов А.В.',
        study: 'Тазобедренный сустав',
        date: '14.03.2025',
        gender: 'Мужчина',
        age: '6 мес.',
    },
];

const fallbackLandmarks = [
    { id: 'pelvis-y-cartilage-left', category: 'pelvis', name: 'Левый Y-образный хрящ', checked: true },
    { id: 'pelvis-y-cartilage-right', category: 'pelvis', name: 'Правый Y-образный хрящ', checked: true },
    { id: 'femur-head', category: 'femur', name: 'Головка бедренной кости', checked: true },
];

export function DoctorViewer() {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const patientIdFromUrl = searchParams.get('patientId');

    const [activeTool, setActiveTool] = useState('Pan');
    const [search, setSearch] = useState('');
    const [patients, setPatients] = useState([]);
    const [activePatientId, setActivePatientId] = useState(patientIdFromUrl);
    const [landmarks, setLandmarks] = useState([]);
    const [results, setResults] = useState([]);
    const [confidence, setConfidence] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const load = async () => {
            setLoading(true);
            setError(null);

            try {
                const patientsData = await api.getPatients();
                setPatients(patientsData);
                if (!activePatientId && patientsData.length > 0) {
                    setActivePatientId(patientsData[0]?.id ?? null);
                }
            } catch (err) {
                console.error('Failed to load patients', err);
                setPatients(fallbackPatients);
                if (!activePatientId) {
                    setActivePatientId(fallbackPatients[0]?.id ?? null);
                }
            } finally {
                setLoading(false);
            }
        };

        load();
    }, [activePatientId, patientIdFromUrl]);

    useEffect(() => {
        if (!activePatientId) return;

        const loadPatientData = async () => {
            try {
                const [landmarksData, resultsData, confidenceData] = await Promise.all([
                    api.getLandmarks(activePatientId),
                    api.getResults(activePatientId),
                    api.getConfidence(activePatientId),
                ]);

                setLandmarks(landmarksData.map((lm) => ({ ...lm, checked: lm.checked ?? true })));
                setResults(resultsData);
                setConfidence(confidenceData?.value ?? null);
            } catch (err) {
                console.error('Failed to load patient data', err);
                setLandmarks(fallbackLandmarks);
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

    return (
        <div className="doctor-viewer">
            <header className="doctor-viewer__header">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => navigate('/')}
                    className="doctor-viewer__home-btn"
                >
                    <House size={20} />
                </Button>
                <h1 className="doctor-viewer__title">Режим Врача</h1>
            </header>

            <div className="doctor-viewer__main">
                <aside className="doctor-viewer__sidebar">
                    <div className="doctor-viewer__sidebar-header">
                        <h2 className="doctor-viewer__sidebar-title">Пациенты</h2>
                        <Input
                            placeholder="Поиск..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                            className="doctor-viewer__search-input"
                        />
                    </div>

                    <ScrollArea className="doctor-viewer__patient-list scrollbar-thin">
                        {filteredPatients.map((patient) => (
                            <div
                                key={patient.id}
                                className={`doctor-viewer__patient-item ${
                                    activePatientId === patient.id ? 'doctor-viewer__patient-item--active' : ''
                                }`}
                                onClick={() => setActivePatientId(patient.id)}
                            >
                                <Avatar className="doctor-viewer__patient-avatar">
                                    <AvatarFallback>{patient.name.slice(0, 2)}</AvatarFallback>
                                </Avatar>
                                <div className="doctor-viewer__patient-info">
                                    <div className="doctor-viewer__patient-name">{patient.name}</div>
                                    <div className="doctor-viewer__patient-meta">{patient.age || '-'}</div>
                                </div>
                            </div>
                        ))}
                    </ScrollArea>
                </aside>

                <main className="doctor-viewer__content">
                    {activePatient && (
                        <>
                            <div className="doctor-viewer__header-card">
                                <Card>
                                    <CardContent className="doctor-viewer__patient-detail">
                                        <div>
                                            <div className="doctor-viewer__patient-label">Пациент:</div>
                                            <div className="doctor-viewer__patient-value">{activePatient.name}</div>
                                        </div>
                                        <div>
                                            <div className="doctor-viewer__patient-label">ID:</div>
                                            <div className="doctor-viewer__patient-value">{activePatient.id}</div>
                                        </div>
                                        <div>
                                            <div className="doctor-viewer__patient-label">Возраст:</div>
                                            <div className="doctor-viewer__patient-value">{activePatient.age || '-'}</div>
                                        </div>
                                        {confidence !== null && (
                                            <div>
                                                <div className="doctor-viewer__patient-label">Уверенность:</div>
                                                <Badge variant={confidence > 0.7 ? 'default' : 'secondary'}>
                                                    {(confidence * 100).toFixed(1)}%
                                                </Badge>
                                            </div>
                                        )}
                                    </CardContent>
                                </Card>
                            </div>

                            <div className="doctor-viewer__viewer-section">
                                <div className="doctor-viewer__toolbar">
                                    <Toolbar activeTool={activeTool} onToolChange={setActiveTool} />
                                </div>
                                <div className="doctor-viewer__viewer">
                                    <CornerstoneViewer files={[]} activeTool={activeTool} />
                                </div>
                            </div>

                            <div className="doctor-viewer__results-section">
                                <h3 className="doctor-viewer__results-title">Результаты анализа</h3>
                                {results.length > 0 ? (
                                    <div className="doctor-viewer__results-grid">
                                        {results.map((result, idx) => (
                                            <div key={idx} className="doctor-viewer__result-item">
                                                <div className="doctor-viewer__result-param">{result.parameter}</div>
                                                <div className="doctor-viewer__result-values">
                                                    <span>Л: {result.left}</span>
                                                    <span>П: {result.right}</span>
                                                    <span>Норма: {result.normal}</span>
                                                </div>
                                                <Badge variant={result.status === 'success' ? 'default' : 'destructive'}>
                                                    {result.status === 'success' ? 'OK' : 'Аномалия'}
                                                </Badge>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="doctor-viewer__results-empty">Нет данных анализа</div>
                                )}
                            </div>
                        </>
                    )}
                </main>
            </div>
        </div>
    );
}
