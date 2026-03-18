import { useState } from 'react';
import { Upload, AlertCircle, CheckCircle, Loader } from 'lucide-react';
import api from '../../../services/api.js';
import './FileUploader.scss';

export default function FileUploader({ onAnalysisComplete, onError }) {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    const handleFileChange = async (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        const file = files[0];
        setLoading(true);
        setError(null);
        setSuccess(null);

        try {
            // Отправляем файл на анализ
            const result = await api.analyzeImage(file, null);

            // Успешно получили результат с patient_id
            setSuccess(`Анализ завершен! Patient ID: ${result.patient_id}`);
            console.log('Analysis result:', result);

            // Передаем результат родительскому компоненту
            if (onAnalysisComplete) {
                onAnalysisComplete(result);
            }

            // Очищаем input
            e.target.value = '';
        } catch (err) {
            const errorMsg = err.message || 'Ошибка при загрузке файла';
            setError(errorMsg);
            console.error('Upload error:', err);

            if (onError) {
                onError(err);
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="file-uploader">
            <input
                id="file-input"
                type="file"
                accept=".dcm,image/*"
                onChange={handleFileChange}
                disabled={loading}
                className="file-uploader__input"
            />
            <label
                htmlFor="file-input"
                className={`file-uploader__btn ${loading ? 'file-uploader__btn--disabled' : ''}`}
            >
                {loading ? (
                    <>
                        <Loader size={18} strokeWidth={1.5} className="file-uploader__icon-spin" />
                        <span>Обработка...</span>
                    </>
                ) : (
                    <>
                        <Upload size={18} strokeWidth={1.5} />
                        <span>Загрузить</span>
                    </>
                )}
            </label>

            {error && (
                <div className="file-uploader__message file-uploader__message--error">
                    <AlertCircle size={16} />
                    <span>{error}</span>
                </div>
            )}

            {success && (
                <div className="file-uploader__message file-uploader__message--success">
                    <CheckCircle size={16} />
                    <span>{success}</span>
                </div>
            )}
        </div>
    );
}