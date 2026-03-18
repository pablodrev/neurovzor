import { useEffect, useRef } from "react";
import * as cornerstone from "cornerstone-core";
import * as cornerstoneTools from "cornerstone-tools";
import * as cornerstoneMath from "cornerstone-math";
import * as dicomParser from "dicom-parser";
import * as cornerstoneWADOImageLoader from "cornerstone-wado-image-loader";
import Hammer from "hammerjs";

cornerstoneTools.external.cornerstone = cornerstone;
cornerstoneTools.external.cornerstoneMath = cornerstoneMath;
cornerstoneTools.external.Hammer = Hammer;

cornerstoneWADOImageLoader.external.cornerstone = cornerstone;
cornerstoneWADOImageLoader.external.dicomParser = dicomParser;  

cornerstoneWADOImageLoader.configure({ useWebWorkers: false });

export default function CornerstoneViewer({ files, activeTool }) {
    const elementRef = useRef(null);
    const currentImageIdRef = useRef(null);

    function parsePixelSpacingFromDataset(image) {
        try {
            const ds = image && image.data;
            if (!ds || typeof ds.string !== "function") return null;

            const ps = ds.string("x00280030");
            if (ps) {
                const parts = ps.split("\\").map((s) => parseFloat(s));
                if (parts.length === 1) return { row: parts[0], col: parts[0] };
                if (parts.length >= 2) return { row: parts[0], col: parts[1] };
            }

            const ips = ds.string("x00181164");
            if (ips) {
                const parts = ips.split("\\").map((s) => parseFloat(s));
                if (parts.length >= 2) return { row: parts[0], col: parts[1] };
            }
        } catch (e) {
            // ignore
        }
        return null;
    }

    function getPixelSpacing(image) {
        if (!image) return { row: 1, col: 1 };

        if (image.rowPixelSpacing && image.columnPixelSpacing) {
            console.log('Pixel spacing from image properties:', { row: image.rowPixelSpacing, col: image.columnPixelSpacing });
            return { row: image.rowPixelSpacing, col: image.columnPixelSpacing };
        }

        const ps = parsePixelSpacingFromDataset(image);
        if (ps) {
            console.log('Pixel spacing parsed from dataset:', ps);
            return ps;
        }

        if (image.pixelSpacing) {
            console.log('Pixel spacing from image.pixelSpacing:', image.pixelSpacing);
            return { row: image.pixelSpacing[0], col: image.pixelSpacing[1] || image.pixelSpacing[0] };
        }

        console.warn('No pixel spacing found, using default 1.0');
        return { row: 1.0, col: 1.0 };
    }

    // Функция для обновления измерений в мм после каждого взаимодействия
    function updateMeasurementsInMM(element) {
        const image = cornerstone.getImage(element);
        if (!image) return;

        const spacing = getPixelSpacing(image);
        console.log('Spacing used:', spacing);
        // LengthTool
        const lengthToolState = cornerstoneTools.getToolState(element, "Length");
        if (lengthToolState && lengthToolState.data && lengthToolState.data.length) {
            lengthToolState.data.forEach((m) => {
                const h1 = m.handles.start;
                const h2 = m.handles.end;
                const dx = (h2.x - h1.x);
                const dy = (h2.y - h1.y);
                const dx_mm = dx * spacing.col;
                const dy_mm = dy * spacing.row;
                const dist_mm = Math.sqrt(dx_mm * dx_mm + dy_mm * dy_mm);
                console.log('Length measurement:', dist_mm.toFixed(1), 'mm');
                m.lengthInMM = dist_mm;
                m.text = `${dist_mm.toFixed(1)} mm`;
            });
        }

        // AngleTool
        const angleState = cornerstoneTools.getToolState(element, "Angle");
        if (angleState && angleState.data && angleState.data.length) {
            angleState.data.forEach((m) => {
                const a = m.handles.start;
                const b = m.handles.mid;
                const c = m.handles.end;
                function dist_mm(p1, p2) {
                    const dx = (p2.x - p1.x) * spacing.col;
                    const dy = (p2.y - p1.y) * spacing.row;
                    return Math.sqrt(dx * dx + dy * dy);
                }
                m.sideAB_mm = dist_mm(a, b);
                m.sideBC_mm = dist_mm(b, c);
                m.angleDegrees = m.angle ? m.angle : null;
                console.log('Angle measurement:', m.angle ? `${m.angle.toFixed(1)}°` : `${m.sideAB_mm.toFixed(1)} mm`);
                m.text = m.angle ? `${m.angle.toFixed(1)}°` : `${m.sideAB_mm.toFixed(1)} mm`;
            });
        }

        // EllipticalRoiTool (площадь в пикселях → мм^2)
        const elState = cornerstoneTools.getToolState(element, "EllipticalRoi");
        if (elState && elState.data && elState.data.length) {
            elState.data.forEach((m) => {
                // библиотека обычно имеет cachedStats.area (в пикселях) — проверяем
                const areaPx = (m.cachedStats && m.cachedStats.area) ? m.cachedStats.area : null;
                if (areaPx != null) {
                    const pixelArea_mm2 = areaPx * spacing.row * spacing.col;
                    console.log('EllipticalRoi area:', pixelArea_mm2.toFixed(1), 'mm²');
                    m.areaInMM2 = pixelArea_mm2;
                    m.text = `${pixelArea_mm2.toFixed(1)} mm²`;
                }
            });
        }

        // RectangleRoiTool
        const rectState = cornerstoneTools.getToolState(element, "RectangleRoi");
        if (rectState && rectState.data && rectState.data.length) {
            rectState.data.forEach((m) => {
                const h1 = m.handles.start;
                const h2 = m.handles.end;
                const w_px = Math.abs(h2.x - h1.x);
                const h_px = Math.abs(h2.y - h1.y);
                const w_mm = w_px * spacing.col;
                const h_mm = h_px * spacing.row;
                m.width_mm = w_mm;
                m.height_mm = h_mm;
                m.area_mm2 = w_mm * h_mm;
                console.log('RectangleRoi:', w_mm.toFixed(1), '×', h_mm.toFixed(1), 'mm,', m.area_mm2.toFixed(1), 'mm²');
                m.text = `${w_mm.toFixed(1)} × ${h_mm.toFixed(1)} mm\n${m.area_mm2.toFixed(1)} mm²`;
            });
        }

        // FreehandRoiTool
        const freeState = cornerstoneTools.getToolState(element, "FreehandRoi");
        if (freeState && freeState.data && freeState.data.length) {
            freeState.data.forEach((m) => {
                const areaPx = (m.cachedStats && m.cachedStats.area) ? m.cachedStats.area : null;
                if (areaPx != null) {
                    m.areaInMM2 = areaPx * spacing.row * spacing.col;
                    console.log('FreehandRoi area:', m.areaInMM2.toFixed(1), 'mm²');
                    m.text = `${m.areaInMM2.toFixed(1)} mm²`;
                }
            });
        }
        cornerstone.updateImage(element);
    }

    useEffect(() => {
        const element = elementRef.current;
        if (!element) return;

        try {
            cornerstoneTools.init({
                mouseEnabled: true,
                touchEnabled: true
            });
        } catch (e) {
            console.warn("cornerstoneTools.init() warning", e);
        }

        cornerstone.enable(element);

        const {
            LengthTool,
            WwwcTool,
            PanTool,
            ZoomTool,
            MagnifyTool,
            AngleTool,
            EllipticalRoiTool,
            RectangleRoiTool,
            FreehandRoiTool,
            ArrowAnnotateTool,
        } = cornerstoneTools;

        function safeAddTool(ToolClass, name) {
            try {
                if (!ToolClass) {
                    console.warn(`Инструмент  ${name} не найден в cornerstoneTools (несоответствие версий?)`);
                    return;
                }
                cornerstoneTools.addTool(ToolClass);
            } catch (e) {
                console.warn(`addTool fallback ${name}`, e);
                try {
                    cornerstoneTools.addTool(new ToolClass());
                } catch (err) { /* ignore */ }
            }
        }

        safeAddTool(LengthTool, "Length");
        safeAddTool(WwwcTool, "Wwwc");
        safeAddTool(PanTool, "Pan");
        safeAddTool(ZoomTool, "Zoom");
        safeAddTool(MagnifyTool, "Magnify");
        safeAddTool(AngleTool, "Angle");
        safeAddTool(EllipticalRoiTool, "EllipticalRoi");
        safeAddTool(RectangleRoiTool, "RectangleRoi");
        safeAddTool(FreehandRoiTool, "FreehandRoi");
        safeAddTool(ArrowAnnotateTool, "ArrowAnnotate");

        // Включаем основные инструменты (enable)
        const enableNames = ["Length", "Wwwc", "Pan", "Zoom", "Magnify", "Angle", "EllipticalRoi", "RectangleRoi", "FreehandRoi", "ArrowAnnotate", "TextMarker"];
        enableNames.forEach((n) => {
            try { cornerstoneTools.setToolEnabled(n); } catch (e) { /* ignore if not present */ }
        });

        // Устанавливаем стартовый инструмент (Pan)
        try {
            cornerstoneTools.setToolActive("Pan", { mouseButtonMask: 1 });
        } catch (e) { }

        // Повесим listener на mouseup, чтобы обновлять mm-значения после каждого взаимодействия
        const onMouseUp = () => updateMeasurementsInMM(element);
        element.addEventListener("mouseup", onMouseUp);
        element.addEventListener("touchend", onMouseUp);

        // Слушатель события рендеринга для обновления текста измерений на экране
        const onImageRendered = () => {
            const image = cornerstone.getImage(element);
            if (!image) return;

            const spacing = getPixelSpacing(image);

            // Обновляем Length
            const lengthToolState = cornerstoneTools.getToolState(element, "Length");
            if (lengthToolState && lengthToolState.data) {
                lengthToolState.data.forEach((m) => {
                    if (m.handles && m.handles.start && m.handles.end) {
                        const h1 = m.handles.start;
                        const h2 = m.handles.end;
                        const dx = (h2.x - h1.x);
                        const dy = (h2.y - h1.y);
                        const dx_mm = dx * spacing.col;
                        const dy_mm = dy * spacing.row;
                        const dist_mm = Math.sqrt(dx_mm * dx_mm + dy_mm * dy_mm);
                        m.text = `${dist_mm.toFixed(1)} mm`;
                    }
                });
            }

            // Обновляем Angle
            const angleState = cornerstoneTools.getToolState(element, "Angle");
            if (angleState && angleState.data) {
                angleState.data.forEach((m) => {
                    if (m.handles && m.handles.start) {
                        const a = m.handles.start;
                        const b = m.handles.mid;
                        const c = m.handles.end;
                        if (b && c) {
                            function dist_mm(p1, p2) {
                                const dx = (p2.x - p1.x) * spacing.col;
                                const dy = (p2.y - p1.y) * spacing.row;
                                return Math.sqrt(dx * dx + dy * dy);
                            }
                            m.sideAB_mm = dist_mm(a, b);
                            m.sideBC_mm = dist_mm(b, c);
                            m.text = m.angle ? `${m.angle.toFixed(1)}°` : `${m.sideAB_mm.toFixed(1)} mm`;
                        }
                    }
                });
            }
        };
        element.addEventListener("cornerstoneimagerendered", onImageRendered);

        return () => {
            try { element.removeEventListener("mouseup", onMouseUp); } catch (e) { }
            try { element.removeEventListener("touchend", onMouseUp); } catch (e) { }
            try { element.removeEventListener("cornerstoneimagerendered", onImageRendered); } catch (e) { }
            try { cornerstone.disable(element); } catch (e) { }
        };
    }, []);

    // Загрузка изображения
    useEffect(() => {
        async function loadFirstFile() {
            if (!files || files.length === 0) return;
            const file = files[0];
            const element = elementRef.current;

            const isDicom = file.type === "application/dicom" || file.name.toLowerCase().endsWith(".dcm");

            if (isDicom) {
                const imageId = cornerstoneWADOImageLoader.wadouri.fileManager.add(file);
                currentImageIdRef.current = imageId;

                try {
                    const image = await cornerstone.loadAndCacheImage(imageId);

                    const parsed = parsePixelSpacingFromDataset(image);
                    if (parsed) {
                        image.rowPixelSpacing = parsed.row;
                        image.columnPixelSpacing = parsed.col;
                    }

                    cornerstone.displayImage(element, image);
                    cornerstone.fitToWindow(element);

                    updateMeasurementsInMM(element);
                } catch (error) {
                    console.error("Ошибка загрузки DICOM:", error);
                }
            } else {
                // Web image (PNG/JPG)
                const imageId = URL.createObjectURL(file);
                currentImageIdRef.current = imageId;

                const img = new Image();
                img.src = imageId;
                img.onload = async () => {
                    const image = {
                        imageId,
                        minPixelValue: 0,
                        maxPixelValue: 255,
                        slope: 1.0,
                        intercept: 0,
                        windowCenter: 127,
                        windowWidth: 255,
                        rows: img.naturalHeight,
                        columns: img.naturalWidth,
                        height: img.naturalHeight,
                        width: img.naturalWidth,
                        getPixelData: () => {
                            const canvas = document.createElement("canvas");
                            canvas.width = img.naturalWidth;
                            canvas.height = img.naturalHeight;
                            const ctx = canvas.getContext("2d");
                            ctx.drawImage(img, 0, 0);
                            return ctx.getImageData(0, 0, canvas.width, canvas.height).data;
                        },
                        color: true
                    };

                    image.rowPixelSpacing = image.rowPixelSpacing || 1.0;
                    image.columnPixelSpacing = image.columnPixelSpacing || 1.0;

                    try {
                        cornerstone.displayImage(element, image);
                        cornerstone.fitToWindow(element);
                        updateMeasurementsInMM(element);
                    } catch (error) {
                        console.error("Ошибка отображения веб-изображения:", error);
                    }
                };
                img.onerror = (e) => console.error("Ошибка загрузки изображения:", e);
            }
        }

        loadFirstFile();
    }, [files]);

    useEffect(() => {
        const element = elementRef.current;
        if (!element) return;

        // сначала сбросим все активные
        // const toolNames = ["Length", "Wwwc", "Pan", "Zoom", "Magnify", "Angle", "EllipticalRoi", "RectangleRoi", "FreehandRoi", "ArrowAnnotate", "TextMarker"];
        // toolNames.forEach((n) => {
        //     try { cornerstoneTools.setToolDisabled(n); } catch (e) { }
        // });

        // активируем выбранный
        try {
            if (activeTool === "Length") {
                cornerstoneTools.setToolActive("Length", { mouseButtonMask: 1 });
            } else if (activeTool === "Angle") {
                cornerstoneTools.setToolActive("Angle", { mouseButtonMask: 1 });
            } else if (activeTool === "EllipticalRoi") {
                cornerstoneTools.setToolActive("EllipticalRoi", { mouseButtonMask: 1 });
            } else if (activeTool === "RectangleRoi") {
                cornerstoneTools.setToolActive("RectangleRoi", { mouseButtonMask: 1 });
            } else if (activeTool === "FreehandRoi") {
                cornerstoneTools.setToolActive("FreehandRoi", { mouseButtonMask: 1 });
            } else if (activeTool === "Wwwc") {
                cornerstoneTools.setToolActive("Wwwc", { mouseButtonMask: 1 });
            } else if (activeTool === "Magnify") {
                cornerstoneTools.setToolActive("Magnify", { mouseButtonMask: 1 });
            } else if (activeTool === "Pan") {
                cornerstoneTools.setToolActive("Pan", { mouseButtonMask: 1 });
            } else if (activeTool === "Zoom") {
                cornerstoneTools.setToolActive("Zoom", { mouseButtonMask: 1 });
            } else if (activeTool === "Text") {
                try {
                    cornerstoneTools.setToolActive("ArrowAnnotate", { mouseButtonMask: 1 });
                } catch (e) {
                    console.warn("Не удалось активировать ArrowAnnotate", e);
                }   
            }
        } catch (e) {
            console.warn("Проблема с активацией инструмента", e);
        }
    }, [activeTool]);

    return (
        <div style={{ width: "100%", height: "100%" }}>
            <div
                ref={elementRef}
                style={{
                    width: "100%",
                    height: "100%",
                    background: "black",
                    position: "relative",
                }}
            />
        </div>
    );
}