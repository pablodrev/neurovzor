import {
    ZoomIn,
    Hand,
    Ruler,
    CornerDownRight,
    SlidersHorizontal,
    Search,
    Circle,
    Square,
    Pencil,
    Type,
    ChevronDown
} from "lucide-react";
import { useState } from 'react';
import './Toolbar.scss';

export default function Toolbar({ activeTool, setActiveTool }) {
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    const mainTools = [
        { id: "Zoom", label: "Zoom", icon: ZoomIn },
        { id: "Pan", label: "Pan", icon: Hand },
        { id: "Wwwc", label: "Контраст", icon: SlidersHorizontal },
        { id: "Magnify", label: "Лупа", icon: Search },
    ];

    const measurementTools = [
        { id: "Length", label: "Линейка", icon: Ruler },
        { id: "Angle", label: "Угол", icon: CornerDownRight },
        { id: "EllipticalRoi", label: "Эллипс", icon: Circle },
        { id: "RectangleRoi", label: "Прямоугольник", icon: Square },
        { id: "FreehandRoi", label: "Контур", icon: Pencil },
        { id: "Text", label: "Подпись", icon: Type }
    ];

    const activeMeasurementTool = measurementTools.find(t => t.id === activeTool);

    const handleSelectTool = (toolId) => {
        setActiveTool(toolId);
        setIsDropdownOpen(false);
    };

    return (
        <div className="toolbar">
            {mainTools.map(tool => {
                const Icon = tool.icon;

                return (
                    <button
                        key={tool.id}
                        onClick={() => setActiveTool(tool.id)}
                        className={`toolbar__btn ${activeTool === tool.id ? 'toolbar__btn--active' : ''}`}
                        title={tool.label}
                    >
                        <Icon size={18} strokeWidth={1.5} />
                        <span className="toolbar__label">{tool.label}</span>
                    </button>
                );
            })}

            {/* Dropdown для инструментов измерения */}
            <div className="toolbar__dropdown">
                <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className={`toolbar__btn toolbar__btn--dropdown ${activeMeasurementTool ? 'toolbar__btn--active' : ''}`}
                    title="Инструменты измерения"
                >
                    {activeMeasurementTool ? (
                        <>
                            {(() => {
                                const Icon = activeMeasurementTool.icon;
                                return <Icon size={18} strokeWidth={1.5} />;
                            })()}
                            <span className="toolbar__label">{activeMeasurementTool.label}</span>
                        </>
                    ) : (
                        <>
                            <Ruler size={18} strokeWidth={1.5} />
                            <span className="toolbar__label">Измерения</span>
                        </>
                    )}
                    <ChevronDown size={16} strokeWidth={1.5} className={`toolbar__chevron ${isDropdownOpen ? 'toolbar__chevron--open' : ''}`} />
                </button>

                {isDropdownOpen && (
                    <div className="toolbar__dropdown-menu">
                        {measurementTools.map(tool => {
                            const Icon = tool.icon;

                            return (
                                <button
                                    key={tool.id}
                                    onClick={() => handleSelectTool(tool.id)}
                                    className={`toolbar__dropdown-item ${activeTool === tool.id ? 'toolbar__dropdown-item--active' : ''}`}
                                >
                                    <Icon size={16} strokeWidth={1.5} />
                                    <span>{tool.label}</span>
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}