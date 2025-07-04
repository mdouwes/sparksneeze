#!/bin/bash

# SVG to Website Assets Generator

set -e

ASSETS_DIR="."

# Check if assets directory exists
if [ ! -d "$ASSETS_DIR" ]; then
    echo "Error: Assets directory '$ASSETS_DIR' not found"
    exit 1
fi

# Check if required tools are installed (prefer Inkscape for better SVG text rendering)
if command -v inkscape &> /dev/null; then
    CONVERTER="inkscape"
    echo "Using Inkscape for SVG conversion (better text rendering)"
elif command -v rsvg-convert &> /dev/null; then
    CONVERTER="rsvg-convert"
    echo "Using rsvg-convert for SVG conversion"
elif command -v gm &> /dev/null; then
    CONVERTER="gm"
    echo "Using GraphicsMagick for SVG conversion (may have font issues)"
else
    echo "Error: No suitable SVG converter found"
    echo "Install one of the following:"
    echo "  Inkscape (recommended): sudo apt-get install inkscape"
    echo "  rsvg-convert: sudo apt-get install librsvg2-bin"
    echo "  GraphicsMagick: sudo apt-get install graphicsmagick"
    exit 1
fi

# Check if required fonts are available
check_font_availability() {
    local font_name=$1
    if command -v fc-list &> /dev/null; then
        if ! fc-list | grep -qi "$font_name"; then
            echo "Warning: Font '$font_name' not found on system"
            echo "  This may cause fallback fonts to be used in SVG rendering"
            echo "  Install '$font_name' for optimal rendering"
            return 1
        fi
    else
        echo "Warning: fontconfig not available - cannot check font availability"
        echo "  Install fontconfig to verify fonts are available"
        return 1
    fi
    return 0
}

# Function to extract fonts from SVG files
extract_fonts_from_svg() {
    local svg_file=$1
    if [ -f "$svg_file" ]; then
        # Extract font-family values from SVG, handling various formats
        grep -oE 'font-family[[:space:]]*:[[:space:]]*[^;"}]+' "$svg_file" 2>/dev/null | \
        sed 's/font-family[[:space:]]*:[[:space:]]*//' | \
        sed "s/['\"]//g" | \
        sed 's/[[:space:]]*,.*$//' | \
        sort -u
    fi
}

# Check fonts in all SVG files
echo "Checking font availability..."
for svg_file in *.svg; do
    if [ -f "$svg_file" ]; then
        echo "Analyzing fonts in $(basename "$svg_file")..."
        fonts=$(extract_fonts_from_svg "$svg_file")
        if [ -n "$fonts" ]; then
            echo "$fonts" | while read -r font; do
                if [ -n "$font" ]; then
                    check_font_availability "$font"
                fi
            done
        else
            echo "  No custom fonts detected in $(basename "$svg_file")"
        fi
    fi
done

# Cleanup function - remove generated assets but preserve SVGs
cleanup_assets() {
    echo "Cleaning up existing generated assets..."
    
    # Remove favicon directory but keep SVGs
    if [ -d "favicon" ]; then
        rm -rf "favicon"
    fi
    
    # Remove logo directory but keep SVGs
    if [ -d "logo" ]; then
        rm -rf "logo"
    fi
    
    # Remove banner directory but keep SVGs
    if [ -d "banner" ]; then
        rm -rf "banner"
    fi
}

# Clean up existing assets
cleanup_assets

# Function to generate PNG from SVG
generate_png() {
    local input_svg=$1
    local size=$2
    local output_file=$3
    
    case $CONVERTER in
        "inkscape")
            inkscape --export-type=png --export-filename="$output_file" --export-width="$size" --export-height="$size" "$input_svg"
            ;;
        "rsvg-convert")
            rsvg-convert -w "$size" -h "$size" -o "$output_file" "$input_svg"
            ;;
        "gm")
            gm convert -background none "$input_svg" -resize "${size}x${size}" "$output_file"
            ;;
    esac
}

# Function to generate WebP from SVG
generate_webp() {
    local input_svg=$1
    local size=$2
    local output_file=$3
    
    case $CONVERTER in
        "inkscape")
            # Inkscape doesn't support WebP directly, convert via PNG
            local temp_png="${output_file%.webp}.temp.png"
            inkscape --export-type=png --export-filename="$temp_png" --export-width="$size" --export-height="$size" "$input_svg"
            if command -v cwebp &> /dev/null; then
                cwebp "$temp_png" -o "$output_file"
                rm "$temp_png"
            else
                # Fallback to ImageMagick/GraphicsMagick if cwebp not available
                if command -v convert &> /dev/null; then
                    convert "$temp_png" "$output_file"
                    rm "$temp_png"
                elif command -v gm &> /dev/null; then
                    gm convert "$temp_png" "$output_file"
                    rm "$temp_png"
                else
                    echo "Warning: Cannot convert to WebP, keeping PNG"
                    mv "$temp_png" "${output_file%.webp}.png"
                fi
            fi
            ;;
        "rsvg-convert")
            # rsvg-convert doesn't support WebP directly, convert via PNG
            local temp_png="${output_file%.webp}.temp.png"
            rsvg-convert -w "$size" -h "$size" -o "$temp_png" "$input_svg"
            if command -v cwebp &> /dev/null; then
                cwebp "$temp_png" -o "$output_file"
                rm "$temp_png"
            else
                # Fallback to ImageMagick/GraphicsMagick if cwebp not available
                if command -v convert &> /dev/null; then
                    convert "$temp_png" "$output_file"
                    rm "$temp_png"
                elif command -v gm &> /dev/null; then
                    gm convert "$temp_png" "$output_file"
                    rm "$temp_png"
                else
                    echo "Warning: Cannot convert to WebP, keeping PNG"
                    mv "$temp_png" "${output_file%.webp}.png"
                fi
            fi
            ;;
        "gm")
            gm convert -background none "$input_svg" -resize "${size}x${size}" "$output_file"
            ;;
    esac
}

# Function to generate square PNG from SVG (for logo)
generate_square_png() {
    local input_svg=$1
    local size=$2
    local output_file=$3
    generate_png "$input_svg" "$size" "$output_file"
}

# Function to generate banner-style PNG (maintains aspect ratio)
generate_banner_png() {
    local input_svg=$1
    local width=$2
    local output_file=$3
    
    case $CONVERTER in
        "inkscape")
            inkscape --export-type=png --export-filename="$output_file" --export-width="$width" "$input_svg"
            ;;
        "rsvg-convert")
            rsvg-convert -w "$width" -o "$output_file" "$input_svg"
            ;;
        "gm")
            gm convert -background none "$input_svg" -resize "${width}x" "$output_file"
            ;;
    esac
}

# Function to generate banner-style WebP (maintains aspect ratio)
generate_banner_webp() {
    local input_svg=$1
    local width=$2
    local output_file=$3
    
    case $CONVERTER in
        "inkscape")
            # Inkscape doesn't support WebP directly, convert via PNG
            local temp_png="${output_file%.webp}.temp.png"
            inkscape --export-type=png --export-filename="$temp_png" --export-width="$width" "$input_svg"
            if command -v cwebp &> /dev/null; then
                cwebp "$temp_png" -o "$output_file"
                rm "$temp_png"
            else
                # Fallback to ImageMagick/GraphicsMagick if cwebp not available
                if command -v convert &> /dev/null; then
                    convert "$temp_png" "$output_file"
                    rm "$temp_png"
                elif command -v gm &> /dev/null; then
                    gm convert "$temp_png" "$output_file"
                    rm "$temp_png"
                else
                    echo "Warning: Cannot convert to WebP, keeping PNG"
                    mv "$temp_png" "${output_file%.webp}.png"
                fi
            fi
            ;;
        "rsvg-convert")
            # rsvg-convert doesn't support WebP directly, convert via PNG
            local temp_png="${output_file%.webp}.temp.png"
            rsvg-convert -w "$width" -o "$temp_png" "$input_svg"
            if command -v cwebp &> /dev/null; then
                cwebp "$temp_png" -o "$output_file"
                rm "$temp_png"
            else
                # Fallback to ImageMagick/GraphicsMagick if cwebp not available
                if command -v convert &> /dev/null; then
                    convert "$temp_png" "$output_file"
                    rm "$temp_png"
                elif command -v gm &> /dev/null; then
                    gm convert "$temp_png" "$output_file"
                    rm "$temp_png"
                else
                    echo "Warning: Cannot convert to WebP, keeping PNG"
                    mv "$temp_png" "${output_file%.webp}.png"
                fi
            fi
            ;;
        "gm")
            gm convert -background none "$input_svg" -resize "${width}x" "$output_file"
            ;;
    esac
}

# Generate favicons from logo.svg
if [ -f "logo.svg" ]; then
    echo "Generating favicons from logo.svg..."
    FAVICON_DIR="favicon"
    mkdir -p "$FAVICON_DIR"
    
    # Web favicons
    generate_png "logo.svg" 16 "$FAVICON_DIR/favicon-16x16.png"
    generate_png "logo.svg" 32 "$FAVICON_DIR/favicon-32x32.png"
    generate_png "logo.svg" 48 "$FAVICON_DIR/favicon-48x48.png"
    generate_png "logo.svg" 96 "$FAVICON_DIR/favicon-96x96.png"
    generate_png "logo.svg" 192 "$FAVICON_DIR/favicon-192x192.png"
    generate_png "logo.svg" 512 "$FAVICON_DIR/favicon-512x512.png"

    # Generate ICO file - simple fallback approach
    echo "Warning: ICO generation skipped (GraphicsMagick doesn't support ICO format well)"
    echo "Using PNG fallback for favicon.ico"
    cp "$FAVICON_DIR/favicon-32x32.png" "$FAVICON_DIR/favicon.ico"

    # Android icons
    generate_png "logo.svg" 36 "$FAVICON_DIR/android-icon-36x36.png"
    generate_png "logo.svg" 48 "$FAVICON_DIR/android-icon-48x48.png"
    generate_png "logo.svg" 72 "$FAVICON_DIR/android-icon-72x72.png"
    generate_png "logo.svg" 96 "$FAVICON_DIR/android-icon-96x96.png"
    generate_png "logo.svg" 144 "$FAVICON_DIR/android-icon-144x144.png"
    generate_png "logo.svg" 192 "$FAVICON_DIR/android-icon-192x192.png"
    generate_png "logo.svg" 512 "$FAVICON_DIR/android-icon-512x512.png"

    # iOS icons
    generate_png "logo.svg" 57 "$FAVICON_DIR/apple-icon-57x57.png"
    generate_png "logo.svg" 60 "$FAVICON_DIR/apple-icon-60x60.png"
    generate_png "logo.svg" 72 "$FAVICON_DIR/apple-icon-72x72.png"
    generate_png "logo.svg" 76 "$FAVICON_DIR/apple-icon-76x76.png"
    generate_png "logo.svg" 114 "$FAVICON_DIR/apple-icon-114x114.png"
    generate_png "logo.svg" 120 "$FAVICON_DIR/apple-icon-120x120.png"
    generate_png "logo.svg" 144 "$FAVICON_DIR/apple-icon-144x144.png"
    generate_png "logo.svg" 152 "$FAVICON_DIR/apple-icon-152x152.png"
    generate_png "logo.svg" 180 "$FAVICON_DIR/apple-icon-180x180.png"
    generate_png "logo.svg" 167 "$FAVICON_DIR/apple-icon-167x167.png"

    # Apple touch icons
    generate_png "logo.svg" 180 "$FAVICON_DIR/apple-touch-icon.png"
    generate_png "logo.svg" 152 "$FAVICON_DIR/apple-touch-icon-152x152.png"
    generate_png "logo.svg" 167 "$FAVICON_DIR/apple-touch-icon-167x167.png"
    generate_png "logo.svg" 180 "$FAVICON_DIR/apple-touch-icon-180x180.png"

    # Microsoft/Windows icons
    generate_png "logo.svg" 70 "$FAVICON_DIR/ms-icon-70x70.png"
    generate_png "logo.svg" 144 "$FAVICON_DIR/ms-icon-144x144.png"
    generate_png "logo.svg" 150 "$FAVICON_DIR/ms-icon-150x150.png"
    generate_png "logo.svg" 310 "$FAVICON_DIR/ms-icon-310x310.png"

    # Generate HTML snippet
    cat > "$FAVICON_DIR/favicon-html.html" << 'EOF'
<!-- Favicon and App Icons -->
<!-- Standard favicons -->
<link rel="icon" type="image/png" sizes="16x16" href="/favicon/favicon-16x16.png">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon/favicon-48x48.png">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon/favicon-96x96.png">
<link rel="icon" type="image/png" sizes="192x192" href="/favicon/favicon-192x192.png">
<link rel="shortcut icon" href="/favicon/favicon.ico">

<!-- Apple Touch Icons -->
<link rel="apple-touch-icon" sizes="57x57" href="/favicon/apple-icon-57x57.png">
<link rel="apple-touch-icon" sizes="60x60" href="/favicon/apple-icon-60x60.png">
<link rel="apple-touch-icon" sizes="72x72" href="/favicon/apple-icon-72x72.png">
<link rel="apple-touch-icon" sizes="76x76" href="/favicon/apple-icon-76x76.png">
<link rel="apple-touch-icon" sizes="114x114" href="/favicon/apple-icon-114x114.png">
<link rel="apple-touch-icon" sizes="120x120" href="/favicon/apple-icon-120x120.png">
<link rel="apple-touch-icon" sizes="144x144" href="/favicon/apple-icon-144x144.png">
<link rel="apple-touch-icon" sizes="152x152" href="/favicon/apple-icon-152x152.png">
<link rel="apple-touch-icon" sizes="167x167" href="/favicon/apple-icon-167x167.png">
<link rel="apple-touch-icon" sizes="180x180" href="/favicon/apple-icon-180x180.png">

<!-- Android Chrome -->
<link rel="icon" type="image/png" sizes="36x36" href="/favicon/android-icon-36x36.png">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon/android-icon-48x48.png">
<link rel="icon" type="image/png" sizes="72x72" href="/favicon/android-icon-72x72.png">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon/android-icon-96x96.png">
<link rel="icon" type="image/png" sizes="144x144" href="/favicon/android-icon-144x144.png">
<link rel="icon" type="image/png" sizes="192x192" href="/favicon/android-icon-192x192.png">

<!-- Microsoft Windows -->
<meta name="msapplication-TileColor" content="#ffffff">
<meta name="msapplication-TileImage" content="/favicon/ms-icon-144x144.png">
<meta name="msapplication-square70x70logo" content="/favicon/ms-icon-70x70.png">
<meta name="msapplication-square150x150logo" content="/favicon/ms-icon-150x150.png">
<meta name="msapplication-wide310x150logo" content="/favicon/ms-icon-310x310.png">
<meta name="msapplication-square310x310logo" content="/favicon/ms-icon-310x310.png">

<!-- Additional Meta Tags for Better App Support -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Your App Name">
<meta name="mobile-web-app-capable" content="yes">
<meta name="application-name" content="Your App Name">
EOF
fi

# Generate logo assets from logo.svg
if [ -f "logo.svg" ]; then
    echo "Generating logo assets from logo.svg..."
    LOGO_DIR="logo"
    mkdir -p "$LOGO_DIR"
    
    # Logo PNG files (square)
    generate_square_png "logo.svg" 256 "$LOGO_DIR/logo-small.png"
    generate_square_png "logo.svg" 512 "$LOGO_DIR/logo-medium.png"
    generate_square_png "logo.svg" 1024 "$LOGO_DIR/logo-large.png"
    generate_square_png "logo.svg" 2048 "$LOGO_DIR/logo-superlarge.png"
    
    # Logo WebP files (square)
    generate_webp "logo.svg" 256 "$LOGO_DIR/logo-small.webp"
    generate_webp "logo.svg" 512 "$LOGO_DIR/logo-medium.webp"
    generate_webp "logo.svg" 1024 "$LOGO_DIR/logo-large.webp"
    generate_webp "logo.svg" 2048 "$LOGO_DIR/logo-superlarge.webp"
fi

# Generate banner assets from banner.svg
if [ -f "banner.svg" ]; then
    echo "Generating banner assets from banner.svg..."
    BANNER_DIR="banner"
    mkdir -p "$BANNER_DIR"
    
    # Banner PNG files (maintains aspect ratio) - using consistent sizing with logos
    generate_banner_png "banner.svg" 256 "$BANNER_DIR/banner-small.png"
    generate_banner_png "banner.svg" 512 "$BANNER_DIR/banner-medium.png"
    generate_banner_png "banner.svg" 1024 "$BANNER_DIR/banner-large.png"
    generate_banner_png "banner.svg" 2048 "$BANNER_DIR/banner-superlarge.png"
    
    # Banner WebP files (maintains aspect ratio) - using consistent sizing with logos
    generate_banner_webp "banner.svg" 256 "$BANNER_DIR/banner-small.webp"
    generate_banner_webp "banner.svg" 512 "$BANNER_DIR/banner-medium.webp"
    generate_banner_webp "banner.svg" 1024 "$BANNER_DIR/banner-large.webp"
    generate_banner_webp "banner.svg" 2048 "$BANNER_DIR/banner-superlarge.webp"
fi

echo "✅ Asset generation complete!"
