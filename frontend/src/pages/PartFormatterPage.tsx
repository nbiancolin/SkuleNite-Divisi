import { useState } from "react";
import {
  Container,
  FileInput,
  Button,
  Title,
  Loader,
  Center,
  Text,
  Notification,
  Group,
  TextInput,
  Collapse, 
} from "@mantine/core";
import { Check, X, UploadCloud } from "lucide-react";
import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_URL;

export default function PartFormatterPage() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isFormatting, setIsFormatting] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [msczUrl, setMsczUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // New states
  const [selectedStyle, setSelectedStyle] = useState<"jazz" | "broadway" | "classical" | null>(null);
  const [showTitle, setShowTitle] = useState("");
  const [showNumber, setShowNumber] = useState("");
  const [measuresPerLine, setMeasuresPerLine] = useState<string>("6")
  const [versionNum, setVersionNum] = useState<string>("1.0.0")
  const [composer, setComposer] = useState<string>("")
  const [arranger, setArranger] = useState<string>("")

  const handleUpload = async () => {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setDownloadUrl(null);
    setMsczUrl(null);
    setSessionId(null);
    setSelectedStyle(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API_BASE_URL}/upload-mscz/`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
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

  const handleStyleSelect = (style: "jazz" | "broadway" | "classical") => {
    setSelectedStyle(style);
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
      const response = await axios.post(`${API_BASE_URL}/format-mscz/`, {
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
      });

      setDownloadUrl(response.data.score_download_url);
      setMsczUrl(response.data.mscz_download_url);
    } catch (err: any) {
      console.error("Formatting error:", err);
      setError(err.response?.data?.detail || "Formatting failed.");
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
      <Text>If you would like part formatted as well, make sure to "open all" the parts in the Musescore File first!</Text>
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

      {sessionId && !isFormatting && !downloadUrl && !selectedStyle && (
        <Center mt="xl">
          <div>
            <Text mb="sm" ta="center">
              Choose a style to format your file:
            </Text>
            <Group justify="center">
              <Button onClick={() => handleStyleSelect("jazz")}>Jazz</Button>
              <Button onClick={() => handleStyleSelect("broadway")}>Broadway</Button>
              <Button onClick={() => handleStyleSelect("classical")}>Classical</Button>
            </Group>
          </div>
        </Center>
      )}

      {selectedStyle && (
        <div>
        <Center mt="md">
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
        </div>
      )}

      {selectedStyle === "broadway" && (
        <Center mt="xl">
          <div style={{ width: "100%" }}>
            <Text mb="sm" ta="center">
              Enter show details:
            </Text>
            <TextInput
              label="Show Title"
              value={showTitle}
              onChange={(e) => setShowTitle(e.currentTarget.value)}
              mb="md"
              required
            />
            <TextInput
              label="Show Number"
              value={showNumber}
              onChange={(e) => setShowNumber(e.currentTarget.value)}
              mb="md"
              required
            />
            <TextInput
              label="Composer"
              value={composer}
              onChange={(e) => setComposer(e.currentTarget.value)}
              mb="md"
            />
            <TextInput
              label="Arranger"
              value={arranger}
              onChange={(e) => setArranger(e.currentTarget.value)}
              mb="md"
            />
            {/* TODO[SC-XX] add ticky box to re-format composer text with above info  */}
            <Button onClick={handleFormatRequest} fullWidth>
              Format Musescore File
            </Button>
          </div>
        </Center>
      )}

      {(selectedStyle === "jazz" || selectedStyle === "classical") && (
        <Center mt="xl">
          <div style={{ width: "100%" }}>
            <TextInput
              label="Composer"
              value={composer}
              onChange={(e) => setComposer(e.currentTarget.value)}
              mb="md"
            />
            <TextInput
              label="Arranger"
              value={arranger}
              onChange={(e) => setArranger(e.currentTarget.value)}
              mb="md"
            />
            {/* TODO[SC-XX] add ticky box to re-format composer text with above info  */}
            <Button onClick={handleFormatRequest}>Format Musescore File</Button>
          </div>
        </Center>
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
