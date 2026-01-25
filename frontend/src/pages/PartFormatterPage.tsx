import { useState, useEffect } from "react";
import {
  Container,
  FileInput,
  Button,
  Title,
  Loader,
  Center,
  Text,
  Notification,
  TextInput,
  Collapse,
  Stack,
  Checkbox, 
} from "@mantine/core";
import { Check, X, UploadCloud } from "lucide-react";
import axios from "axios";
import { ScoreTitlePreview } from "../components/ScoreTitlePreview";
import { apiService } from "../services/apiService";

const API_BASE_URL = import.meta.env.VITE_API_URL;

// Helper function to get CSRF token from cookies
function getCsrfToken(): string | null {
  const name = 'csrftoken';
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

export default function PartFormatterPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isFormatting, setIsFormatting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [msczUrl, setMsczUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // New states
  const [selectedStyle, setSelectedStyle] = useState<"jazz" | "broadway" | "classical">("broadway");
  const [showTitle, setShowTitle] = useState("");
  const [showNumber, setShowNumber] = useState("");
  const [measuresPerLine, setMeasuresPerLine] = useState<string>("6")
  const [versionNum, setVersionNum] = useState<string>("1.0.0")
  const [composer, setComposer] = useState<string>("")
  const [arranger, setArranger] = useState<string>("")

  // Check if user is authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await apiService.getCurrentUser();
        setIsAuthenticated(response.is_authenticated);
        // Fetch CSRF token if authenticated to ensure cookie is set
        if (response.is_authenticated) {
          await apiService.fetchCsrfToken();
        }
      } catch (error) {
        console.error('Failed to check authentication:', error);
        setIsAuthenticated(false);
      }
    };
    checkAuth();
  }, []);

  // Helper to get headers with CSRF token if user is authenticated
  const getRequestHeaders = (contentType: string = 'application/json') => {
    const headers: Record<string, string> = {
      'Accept': 'application/json',
    };
    
    // Only set Content-Type if not multipart/form-data (axios sets it automatically)
    if (contentType !== 'multipart/form-data') {
      headers['Content-Type'] = contentType;
    }
    
    // Include CSRF token if user is authenticated
    if (isAuthenticated) {
      const csrfToken = getCsrfToken();
      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
      }
    }
    
    return headers;
  };

  const handleUpload = async () => {
    if (!file) return;

    const allowedTypes = [".mscz"];
    const fileExtension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

    if (!allowedTypes.includes(fileExtension)) {
      setError("Invalid file type. Please upload a .mscz file.");
      setIsUploading(false);
      return;
    }

    setIsUploading(true);
    setError(null);
    setDownloadUrl(null);
    setMsczUrl(null);
    setSessionId(null);
    setSelectedStyle("broadway");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API_BASE_URL}/part-formatter/upload_mscz/`, formData, {
        headers: getRequestHeaders("multipart/form-data"),
        withCredentials: true, // Include cookies for CSRF token
      });

      const id = response.data.session_id;
      if (!id) throw new Error("No session ID returned");
      setSessionId(id);
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFormatRequest = async () => {
    if (!sessionId || !selectedStyle) return;

    if (selectedStyle === "broadway" && (!showTitle || !showNumber)) {
      setError("Please provide both show title and show number.");
      return;
    }

    setIsFormatting(true);
    setError(null);
    setDownloadUrl(null);
    setMsczUrl(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/part-formatter/format_mscz/`, {
        session_id: sessionId,
        style: selectedStyle,
        composer: composer,
        arranger: arranger,
        ...(selectedStyle === "broadway" && {
          show_title: showTitle,
          show_number: showNumber,
        }),
        ...(showAdvanced && {
          measures_per_line: measuresPerLine,
          version_num: versionNum
        })
      }, {
        headers: getRequestHeaders(),
        withCredentials: true, // Include cookies for CSRF token
      });

      setDownloadUrl(response.data.score_download_url);
      setMsczUrl(response.data.mscz_download_url);
    } catch (err: any) {
      console.error("Formatting error:", err);
      setError(err.response?.data?.detail || "Formatting failed.");  //TODO[SC-XX] make this acc display the error at hand
    } finally {
      setIsFormatting(false);
    }
  };

  return (
    <Container size="sm" py="xl">
      <Title ta="center" mb="xl">
        Format a Musescore File!
      </Title>
      <Text>Simply upload your .mscz file, and select your style options, and your Musescore File will be formatted!</Text>
      <Text>If you would like the parts formatted as well, make sure to "open all" the parts in the Musescore File first!</Text>
      <FileInput
        placeholder="Choose a file"
        label="Select file"
        leftSection={<UploadCloud size={18} />}
        value={file}
        onChange={setFile}
        accept="*/*"
        mb="md"
      />

      <Button
        onClick={handleUpload}
        disabled={!file || isUploading}
        fullWidth
        loading={isUploading}
      >
        Upload
      </Button>

      <Text>Note: Your files are only stored on our site while processing. You will retain full ownership of any music uploaded</Text>

      {sessionId && (
        <>
          <Center>
            <Text
              onClick={() => setShowAdvanced((o) => !o)}
              style={{ cursor: "pointer", textDecoration: "underline" }}
              c="blue"
              size="sm"
            >
              {showAdvanced ? "Hide advanced style options" : "Advanced style options"}
            </Text>
          </Center>
            
          <Collapse in={showAdvanced}>
          {/*TODO[SC-42]: Make this value dynamic, and remove manual override */}
            <TextInput
              label="Measures per Line"
              value={measuresPerLine}
              onChange={(e) => setMeasuresPerLine(e.currentTarget.value)}
              type="number"
              mt="md"
            />
            <TextInput
              label="Version Number (1.0.0, 2.2.3, etc)"
              value={versionNum}
              onChange={(e) => setVersionNum(e.currentTarget.value)}
              mt="md"
            />
          </Collapse>
          <ScoreTitlePreview
            selectedStyle={selectedStyle}
            setSelectedStyle={setSelectedStyle}
            title={"Title"}
            subtitle={"subtitle"}
            ensemble={null}
            composer={composer}
            arranger={arranger}
            showTitle={showTitle}
            mvtNo={showNumber}
          />
          {/* <Button onClick={handleFormatRequest}>Format Musescore File</Button> */}
          <Stack mt="xl">
            <TextInput
              label="Title"
              value={"Coming Soon!!"}
              disabled
            />
            <TextInput
              label="Subtitle"
              value={"Coming Soon!!"}
              disabled
            />
            {selectedStyle === "broadway" && (
              <>
                <TextInput
                  label="Show Title"
                  value={showTitle}
                  onChange={(e) => setShowTitle(e.currentTarget.value)}
                  required
                />
                <TextInput
                  label="Show Number"
                  value={showNumber}
                  onChange={(e) => setShowNumber(e.currentTarget.value)}
                  required
                />
              </>
            )}
            <TextInput
              label="Composer"
              value={composer}
              onChange={(e) => setComposer(e.currentTarget.value)}
            />
            <TextInput
              label="Arranger"
              value={arranger}
              onChange={(e) => setArranger(e.currentTarget.value)}
            />
            <Checkbox
              disabled
              label="Overwrite above info in title box (Coming soon !!)"  
              // TODO[SC-62]: Do this
            />
          </Stack>
          {/* TODO[SC-XX] add ticky box to re-format composer text with above info  */}
          <Button onClick={handleFormatRequest} fullWidth mt="md">
            Format Musescore File
          </Button>
              
          
          
        </>
      )}

      {isFormatting && (
        <Center mt="xl">
          <Loader size="lg" />
        </Center>
      )}

      {downloadUrl && (
        <Notification
          mt="xl"
          icon={<Check size={18} />}
          color="green"
          title="Success"
          onClose={() => setDownloadUrl(null)}
        >
          Your file has been processed.{" "}
          <a
            href={downloadUrl}
            download
            target="_blank"
            rel="noopener noreferrer"
          >
            Click here to download the Score.
          </a><br/>
          <a
            href={msczUrl ?? undefined}
            download
            target="_blank"
            rel="noopener noreferrer"
            >
              Click Here to download the Processed Musescore File.
            </a>
        </Notification>
      )}

      {error && (
        <Notification
          mt="xl"
          icon={<X size={18} />}
          color="red"
          title="Error"
          onClose={() => setError(null)}
        >
          {error}
        </Notification>
      )}
    </Container>
  );
}
