import * as ScrollAreaPrimitive from "@radix-ui/react-scroll-area";
import "./ScrollArea.scss";

const ScrollArea = ({ className = "", children, ...props }) => {
    return (
        <ScrollAreaPrimitive.Root
            data-slot="scroll-area"
            className={`scroll-area ${className}`}
            {...props}
        >
            <ScrollAreaPrimitive.Viewport
                data-slot="scroll-area-viewport"
                className="scroll-area__viewport"
            >
                {children}
            </ScrollAreaPrimitive.Viewport>
            <ScrollBar />
            <ScrollAreaPrimitive.Corner />
        </ScrollAreaPrimitive.Root>
    );
};

const ScrollBar = ({
    className = "",
    orientation = "vertical",
    ...props
}) => {
    return (
        <ScrollAreaPrimitive.ScrollAreaScrollbar
            data-slot="scroll-area-scrollbar"
            orientation={orientation}
            className={`scroll-area__scrollbar scroll-area__scrollbar--${orientation} ${className}`}
            {...props}
        >
            <ScrollAreaPrimitive.ScrollAreaThumb
                data-slot="scroll-area-thumb"
                className="scroll-area__thumb"
            />
        </ScrollAreaPrimitive.ScrollAreaScrollbar>
    );
};

export { ScrollArea, ScrollBar };