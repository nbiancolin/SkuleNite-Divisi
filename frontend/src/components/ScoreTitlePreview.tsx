import {
  Text,
  Box,
  SegmentedControl,
} from "@mantine/core";
import '../fonts.css'

// Define allowed preview style names
export type PreviewStyleName = "broadway" | "classical" | "jazz";

// Define allowed text style keys
type TextStyleKey =
  | "title"
  | "subtitle"
  | "composer"
  | "arranger"
  | "mvtNo"
  | "showTitle"
  | "partName"
  | "ensemble";

// Allowed CSS properties for styles
type TextStyle = Partial<{
  margin: string | number;
  textDecoration: string;
  fontFamily: string;
  fontWeight: string | number;
  fontStyle: string;
  fontSize: string | number;
  whiteSpace: string;
}>;

// The shape of previewStyleOptions
type PreviewStyleOptions = {
  [K in PreviewStyleName]: Partial<Record<TextStyleKey, TextStyle>>;
};

// Props interface
interface ScoreTitlePreviewProps {
  selectedStyle: PreviewStyleName;
  setSelectedStyle: (style: PreviewStyleName) => void;
  title: string | null;
  subtitle: string | null;
  ensemble: string | null;
  composer: string | null;
  arranger: string | null;
  showTitle: string | null;
  mvtNo: string | null;
  pieceNumber: number | null | undefined;
}

export function ScoreTitlePreview({
  selectedStyle,
  setSelectedStyle,
  title,
  subtitle,
  ensemble,
  composer,
  arranger, 
  mvtNo,
  showTitle,
  pieceNumber
}: ScoreTitlePreviewProps) {

  const previewStyleOptions: PreviewStyleOptions = {
    broadway: {
      title: {
        margin: "0 0 8px 0",
        textDecoration: "underline",
        fontFamily: "Palatino, sans-serif",
      },
      subtitle: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Palatino, sans-serif",
      },
      ensemble: {},
      composer: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Palatino, sans-serif",
      },
      arranger: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Palatino, sans-serif",
        fontStyle: "italic",
      },
      mvtNo: {
        margin: 0,
        fontSize: "1.5rem",
        fontFamily: "Palatino, sans-serif",
      },
      showTitle: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Palatino, sans-serif",
        textDecoration: "underline",
        whiteSpace: "nowrap",
      },
      partName: {
        fontFamily: "Palatino, sans-serif",
      },
    },
    classical: {
      title: {
        margin: "0 0 8px 0",
        textDecoration: "underline",
        fontFamily: "Palatino, sans-serif",
      },
      subtitle: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Palatino, sans-serif",
      },
      ensemble: {
        margin: "0",
        fontWeight: "bold",
        fontFamily: "Palatino, sans-serif",
      },
      composer: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Palatino, sans-serif",
      },
      arranger: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Palatino, sans-serif",
        fontStyle: "italic",
      },
      mvtNo: {},
      showTitle: {},
      partName: {
        fontFamily: "Palatino, sans-serif",
      },
    },
    jazz: {
      title: {
        margin: "0 0 8px 0",
        textDecoration: "underline",
        fontFamily: "Inkpen2, sans-serif",
      },
      subtitle: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Inkpen2, sans-serif",
      },
      ensemble: {
        margin: "0",
        fontWeight: "bold",
        fontFamily: "Inkpen2, sans-serif",
      },
      composer: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Inkpen2, sans-serif",
      },
      arranger: {
        margin: "0",
        fontWeight: "normal",
        fontFamily: "Inkpen2, sans-serif",
      },
      mvtNo: {},
      showTitle: {},
      partName: {
        fontFamily: "Inkpen2, sans-serif",
      },
    },
  };

  return (
    <>
      <SegmentedControl 
        fullWidth
        size="md"
        mt="md"
        value={selectedStyle}
        onChange={(val) => setSelectedStyle(val as PreviewStyleName)}
        data={[
          {label: "Broadway", value: "broadway"},
          {label: "Jazz", value: "jazz"},
          {label: "Classical", value: "classical"},
        ]}
      />
      <Box
        mt="xl"
        mb="xl"
        p="md"
        style={{
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            width: '100%',
            position: 'relative'
        }}
        >
        <Text size="sm" mb="md" style={{ color: '#666' }}>
            Title Preview:
        </Text>
        {title && (
          <Box
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              marginBottom: "1rem"
            }}
          >
            <h3 style={previewStyleOptions[selectedStyle].partName ?? {}}>
              Conductor Score
            </h3>

            {(mvtNo || pieceNumber || showTitle) && selectedStyle === "broadway" && (
              <Box style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                {showTitle && (
                  <span style={previewStyleOptions[selectedStyle].showTitle ?? {}}>
                    {showTitle}
                  </span>
                )}
                <Box
                  style={{
                    border: "1px solid black",
                    padding: "0.25rem 0.75rem",
                  }}
                >
                  <h1 style={previewStyleOptions[selectedStyle].mvtNo ?? {}}>
                    {mvtNo || pieceNumber}
                  </h1>
                </Box>
              </Box>
            )}
          </Box>
        )}
        
        <div style={{ textAlign: 'center' }}>
            {title && (
            <h1 style={previewStyleOptions[selectedStyle].title ?? {}}>
                {title}
            </h1>
            )}
            
            {subtitle && (
            <h3 style={previewStyleOptions[selectedStyle].subtitle ?? {}}>
                {subtitle}
            </h3>
            )}
        </div>
        <div style={{textAlign: 'right'}}>
          {ensemble && (selectedStyle === "jazz" || selectedStyle === "classical" ) && (
            <h4 style={previewStyleOptions[selectedStyle].ensemble ?? {}}>
                {ensemble}
            </h4>
            )}
            {composer && (
            <h4 style={previewStyleOptions[selectedStyle].composer ?? {}}>
                {composer}
            </h4>
            )}
            {arranger && (
              <h4 style={previewStyleOptions[selectedStyle].arranger ?? {}}> 
                arr. {arranger}  
              </h4>
            )}
        </div>
        
        {!title && !subtitle && !mvtNo && (
            <Text style={{ color: '#999', fontStyle: 'italic', textAlign: 'center' }}>
            Fill in the fields above to see a preview of your arrangement header
            </Text>
        )}
        </Box>
      </>
  )
}
