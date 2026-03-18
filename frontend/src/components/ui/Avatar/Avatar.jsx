import * as AvatarPrimitive from "@radix-ui/react-avatar";
import "./Avatar.scss";

const Avatar = ({ className = "", children, ...props }) => {
    return (
        <AvatarPrimitive.Root
            data-slot="avatar"
            className={`avatar ${className}`}
            {...props}
        >
            {children}
        </AvatarPrimitive.Root>
    );
};

const AvatarImage = ({ className = "", ...props }) => {
    return (
        <AvatarPrimitive.Image
            data-slot="avatar-image"
            className={`avatar__image ${className}`}
            {...props}
        />
    );
};

const AvatarFallback = ({ className = "", children, ...props }) => {
    return (
        <AvatarPrimitive.Fallback
            data-slot="avatar-fallback"
            className={`avatar__fallback ${className}`}
            {...props}
        >
            {children}
        </AvatarPrimitive.Fallback>
    );
};

export { Avatar, AvatarImage, AvatarFallback };