import { useNavigate } from 'react-router';
import { useEffect, useState } from 'react';
import { Button } from '../../components/ui/Button/Button';
import { Input } from '../../components/ui/Input/Input';
import { Avatar, AvatarFallback } from '../../components/ui/Avatar/Avatar';
import { Card, CardContent } from '../../components/ui/Card/Card';
import { ScrollArea } from '../../components/ui/ScrollArea/ScrollArea';
import FileUploader from '../../components/ui/FileUploader/FileUploader';
import api from '../../services/api.js';
import './UploadPage.scss';

export function UploadPage() {
    const navigate = useNavigate();
    const [patients, setPatients] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadPatients = async () => {
            try {
                const data = await api.getPatients();
                setPatients(data);
            } catch (err) {
                console.error('Failed to load patients:', err);
            } finally {
                setLoading(false);
            }
        };

        loadPatients();
    }, []);

    const handleAnalysisComplete = ({ result, file }) => {
        // Добавляем нового пациента в список
        const newPatient = {
            id: result.patient_id,
            name: `Пациент ${result.patient_id}`,
            study: 'Тазобедренный сустав',
            date: new Date().toLocaleString('ru-RU'),
        };

        setPatients((prev) => [newPatient, ...prev]);

        // Переходим на страницу просмотра студента и передаём загруженный файл
        navigate(`/student?patientId=${result.patient_id}`, { state: { files: [file] } });
    };

    return (
        <div className="upload-page">
            {/* TopPanel */}
            <header className="upload-page__header">
                <div className="upload-page__logo">
                    <div className="upload-page__logo-container">
                        <span className="upload-page__logo-text">НейроВзор</span>
                        <span className="upload-page__logo-subtext">AI-ассистент ортопеда</span>
                    </div>
                </div>

                <div className="upload-page__user-section">
                    <Button variant="ghost" size="icon" className="upload-page__notification-btn">
                        <svg className="upload-page__notification-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path>
                        </svg>
                    </Button>

                    <div className="upload-page__user-menu">
                        <Avatar className="upload-page__avatar">
                            <AvatarFallback>ДП</AvatarFallback>
                        </Avatar>
                        <svg className="upload-page__chevron" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path d="M19 9l-7 7-7-7" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path>
                        </svg>
                    </div>
                </div>
            </header>

            <div className="upload-page__main">
                {/* LeftPanel */}
                <aside className="upload-page__sidebar">
                    <div className="upload-page__sidebar-header">
                        <h2 className="upload-page__sidebar-title">Список пациентов</h2>
                        <div className="upload-page__search">
                            <span className="upload-page__search-icon">
                                <svg className="upload-page__search-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"></path>
                                </svg>
                            </span>
                            <Input
                                placeholder="Поиск по имени или ID"
                                className="upload-page__search-input"
                            />
                        </div>
                    </div>

                    <ScrollArea className="upload-page__patient-list scrollbar-thin">
                        {patients.map((patient) => (
                            <div
                                key={patient.id}
                                className="upload-page__patient-item"
                                onClick={() => navigate(`/student?patientId=${patient.id}`)}
                            >
                                <div className="upload-page__patient-image"></div>
                                <div className="upload-page__patient-info">
                                    <div>
                                        <div className="upload-page__patient-name">{patient.name}</div>
                                        <div className="upload-page__patient-id">{patient.id}</div>
                                    </div>
                                    <div className="upload-page__patient-meta">
                                        {patient.date}
                                        <br />
                                        <span className="upload-page__patient-study">{patient.study}</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </ScrollArea>
                </aside>

                {/* CentralArea */}
                <main className="upload-page__content scrollbar-thin">
                    <div className="upload-page__upload-section">
                        <Card className="upload-page__upload-card">
                            <CardContent className="upload-page__upload-card-content">
                                {/* X-ray Icon */}
                                <div className="upload-page__upload-icon">
                                    <svg fill="none" height="64" viewBox="0 0 64 64" width="64" xmlns="http://www.w3.org/2000/svg">
                                        <rect fill="#2D3748" height="64" rx="12" width="64"></rect>
                                        <path d="M16 22C16 18.6863 18.6863 16 22 16H42C45.3137 16 48 18.6863 48 22V42C48 45.3137 45.3137 48 42 48H22C18.6863 48 16 45.3137 16 42V22Z" stroke="#8A94A8" strokeWidth="2"></path>
                                        <path d="M22 32H42M32 22V42" stroke="#8A94A8" strokeLinecap="round" strokeWidth="2"></path>
                                        <path d="M26 26L38 38M38 26L26 38" stroke="#8A94A8" strokeLinecap="round" strokeWidth="1.5"></path>
                                    </svg>  
                                </div>

                                <h1 className="upload-page__upload-title">Добавьте рентгеновский снимок</h1>
                                <p className="upload-page__upload-subtitle">Тазобедренный сустав, прямая проекция</p>

                                {/* FileUploader */}
                                <div className="upload-page__upload-actions">
                                    <FileUploader
                                        onAnalysisComplete={handleAnalysisComplete}
                                        onError={(err) => console.error(err)}
                                    />
                                </div>
                            </CardContent>
                        </Card>
                    </div>

                    {/* BottomSection */}
                    <section className="upload-page__recent">
                        <div className="upload-page__recent-header">
                            <h3 className="upload-page__recent-title">Недавние исследования</h3>
                            <a className="upload-page__recent-link" href="#">Все</a>
                        </div>

                        <div className="upload-page__recent-grid">
                            {/* Recent Items */}
                            {/* <div className="upload-page__recent-item" onClick={() => navigate('/student')}>
                                <div className="upload-page__recent-image"></div>
                                <div className="upload-page__recent-info">
                                    <span className="upload-page__recent-name">Иванов</span>
                                    <span className="upload-page__recent-date">14.03</span>
                                </div>
                            </div>

                            <div className="upload-page__recent-item" onClick={() => navigate('/student')}>
                                <div className="upload-page__recent-image"></div>
                                <div className="upload-page__recent-info">
                                    <span className="upload-page__recent-name">Петрова</span>
                                    <span className="upload-page__recent-date">14.03</span>
                                </div>
                            </div>

                            <div className="upload-page__recent-item" onClick={() => navigate('/student')}>
                                <div className="upload-page__recent-image"></div>
                                <div className="upload-page__recent-info">
                                    <span className="upload-page__recent-name">Сидоров</span>
                                    <span className="upload-page__recent-date">13.03</span>
                                </div>
                            </div>

                            <div className="upload-page__recent-item" onClick={() => navigate('/student')}>
                                <div className="upload-page__recent-image"></div>
                                <div className="upload-page__recent-info">
                                    <span className="upload-page__recent-name">Смирнова</span>
                                    <span className="upload-page__recent-date">13.03</span>
                                </div>
                            </div> */}
                        </div>
                    </section>
                </main>
            </div>
        </div>
    );
}