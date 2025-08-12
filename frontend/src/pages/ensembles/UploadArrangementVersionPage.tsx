import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
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
  SegmentedControl,
} from "@mantine/core";
import { X, UploadCloud } from "lucide-react";
import axios from "axios";
import { apiService } from "../../services/apiService";
import type { Arrangement } from "../../services/apiService";

const API_BASE_URL = import.meta.env.VITE_API_URL;

export default function UploadArrangementVersionPage() {
  const { arrangementId = "0"} = useParams();
  const [arrangement, setArrangement] = useState<Arrangement |undefined>(undefined)
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [versionType, setVersionType] = useState<string>("major")
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null);

  // Function to calculate the new version number based on current version and type
  const getNewVersionNumber = (): string => {
    if (!arrangement?.latest_version_num) return "1.0.0";
    
    const currentVersion = arrangement.latest_version_num;
    const versionParts = currentVersion.split('.').map(part => parseInt(part, 10));
    
    // Ensure we have 3 parts (major.minor.patch)
    while (versionParts.length < 3) {
      versionParts.push(0);
    }
    
    let [major, minor, patch] = versionParts;
    
    switch (versionType) {
      case "major":
        major += 1;
        minor = 0;
        patch = 0;
        break;
      case "minor":
        minor += 1;
        patch = 0;
        break;
      case "patch":
        patch += 1;
        break;
      default:
        break;
    }
    
    return `${major}.${minor}.${patch}`;
  };

  useEffect(() => {
      const fetchData = async () => {
        try {
          const [arrangementData] = await Promise.all([
            apiService.getArrangementById(+arrangementId),
          ]);
          setArrangement(arrangementData)
        } catch (err) {
          if (err instanceof Error) {
            setError(err.message);
          }
        }
      };
 
      if (arrangementId) {
        fetchData();
      }
    }, [arrangementId]);

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("arrangement_id", arrangementId)
    formData.append("version_type", versionType)
    try {
      const response = await axios.post(`${API_BASE_URL}/upload-arrangement-version/`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });
      console.log(response)
      navigate(`/app/arrangements/${arrangementId}`)
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <Container size="sm" py="xl">
      <Title ta="center" mb="xl">
        {arrangement?.title}
      </Title>
      <Center>
        <Text> Create a new version: </Text>
      </Center>
      <FileInput
        placeholder="Choose a file"
        label="Select file"
        leftSection={<UploadCloud size={18} />}
        value={file}
        onChange={setFile}
        accept="*/*"
        mb="md"
      />
      <SegmentedControl
        fullWidth
        size="md"
        mt="md"
        value={versionType}
        onChange={setVersionType}
        data={[
          {label: 'Major (1.0.0)', value: "major"},
          {label: 'Minor (0.1.0)', value: "minor"},
          {label: 'Patch (0.0.1)', value: "patch"},
        ]}
      />
      <Center>
        <Checkbox
          disabled
          label="Use Divisi Part Formatter when exporting parts (Coming Soon!)"
          mt="md"
        />
      </Center>
      <Button
        mt="md"
        onClick={handleUpload}
        disabled={!file || isUploading}
        fullWidth
        loading={isUploading}
      >
        Upload Version {getNewVersionNumber()}
      </Button>
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