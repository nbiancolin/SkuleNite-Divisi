import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Container,
  FileInput,
  Button,
  Title,
  Center,
  Text,
  Notification,
  Checkbox,
  SegmentedControl,
  Collapse,
  TextInput,
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
  const [versionType, setVersionType] = useState<string>("major");

  const [measuresPerLineScore, setMeasuresPerLineScore] = useState<string>("8");
  const [measuresPerLinePart, setMeasuresPerLinePart] = useState<string>("6");

  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState<boolean>(false)
  const [enableDivisiFormatting, setEnableDivisiFormatting] = useState<boolean>(true)

  // Function to calculate the new version number based on current version and type
  const getNewVersionNumber = (type?: string): string => {
    if (!arrangement?.latest_version_num) return "1.0.0";
    
    const currentVersion = arrangement.latest_version_num;
    const versionParts = currentVersion.split('.').map(part => parseInt(part, 10));
    
    // Ensure we have 3 parts (major.minor.patch)
    while (versionParts.length < 3) {
      versionParts.push(0);
    }
    
    let [major, minor, patch] = versionParts;

    if (isNaN(major)){
      major = 0
    }

    const targetType = type || versionType;
    
    switch (targetType) {
      case "major":
        major = major + 1;
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
    formData.append("arrangement_id", arrangementId);
    formData.append("version_type", versionType);
    formData.append("num_measures_per_line_score", measuresPerLineScore);
    formData.append("num_measures_per_line_part", measuresPerLinePart);
    formData.append("format_parts", enableDivisiFormatting.toString())
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
          {label: `Major (${getNewVersionNumber("major")})`, value: "major"},
          {label: `Minor (${getNewVersionNumber("minor")})`, value: "minor"},
          {label: `Patch (${getNewVersionNumber("patch")})`, value: "patch"},
        ]}
      />
      <Center>
        <Checkbox
          checked={enableDivisiFormatting}
          onChange={() => setEnableDivisiFormatting((o) => !o)} 
          label="Use Divisi Part Formatter when exporting parts (Coming Soon!)"
          mt="md"
        />
      </Center>
      
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
          <Text> Divisi Part Formatter Configuration:</Text>
          <Text> For most 4/4 songs, the defaults will work.
            If your song is in 3/4 for example, you might want to increase the number.
            If your song is in 12/8 for example, you might want to decrease the number
          </Text>
          <TextInput
            label="Measures per Line (Score)"
            value={measuresPerLineScore}
            onChange={(e) => setMeasuresPerLineScore(e.currentTarget.value)}
            type="number"
            mt="md"
          />
          <TextInput
            label="Measures per Line (Part)"
            value={measuresPerLinePart}
            onChange={(e) => setMeasuresPerLinePart(e.currentTarget.value)}
            mt="md"
          />
          {/* TODO: Add functionality for setting page size and stuff */}
          {/* TODO: Make the above a property of the Ensemble (that can be overrided by the arrangement) */}
            {/* Idea for that: Make a new model called "style properties", and ensembles can select the same as previous (and make their own copy) or custom make their own */}
        </Collapse>

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