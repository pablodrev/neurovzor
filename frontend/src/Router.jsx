import { createBrowserRouter } from "react-router";
import { UploadPage } from "./pages/UploadPage/UploadPage";
import { StudentViewer } from "./pages/StudentViewer/StudentViewer";
import { DoctorViewer } from "./pages/DoctorViewer/DoctorViewer";

export const router = createBrowserRouter([
    {
        path: "/",
        children: [
            { index: true, Component: UploadPage },
            { path: "student", Component: StudentViewer },
            { path: "doctor", Component: DoctorViewer },
        ],
    },
]);
