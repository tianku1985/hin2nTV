package wang.switchy.hin2n.tool;


import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.Closeable;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.RandomAccessFile;
import java.nio.charset.Charset;

/**
 * n2n 边缘节点日志文件读取（模块化后不再依赖任何 RecyclerView 适配器，
 * 界面侧可自行用定时器轮询 {@link #readTxtLimit} 刷新日志展示）。
 * <p>
 * native（slog/fprintf）与 Java（FileWriter）写入的均是 UTF-8 字节，
 * 因此读取时统一按 UTF-8 解码；注意 {@link RandomAccessFile#readLine} 恒按
 * ISO-8859-1 逐字节转字符，会把中文日志显示成乱码，故 {@link #readTxtLimit}
 * 改为读取原始字节后按 UTF-8 解码。
 */
public class IOUtils {

    private static final Charset UTF8 = Charset.forName("UTF-8");

    public static String readTxt(String txtPath) {
        File file = new File(txtPath);
        if (file.isFile() && file.exists()) {
            FileInputStream fileInputStream = null;
            InputStreamReader inputStreamReader = null;
            BufferedReader bufferedReader = null;
            try {
                fileInputStream = new FileInputStream(file);
                inputStreamReader = new InputStreamReader(fileInputStream, UTF8);
                bufferedReader = new BufferedReader(inputStreamReader);
                StringBuilder stringBuilder = new StringBuilder();
                String text;
                while ((text = bufferedReader.readLine()) != null) {
                    stringBuilder.append(text);
                    stringBuilder.append("\n");
                }
                return stringBuilder.toString();
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                close(fileInputStream);
                close(inputStreamReader);
                close(bufferedReader);
            }
        }
        return "";
    }

    /** 读取文件末尾最多 size 字节（日志展示用），按 UTF-8 解码 */
    public static String readTxtLimit(String txtPath, int size) {
        File file = new File(txtPath);
        if (file.exists() && file.isFile()) {
            RandomAccessFile randomAccessFile = null;
            try {
                randomAccessFile = new RandomAccessFile(file, "r");
                long length = randomAccessFile.length();
                long start = 0;
                if (length > size) {
                    start = length - size;
                }
                randomAccessFile.seek(start);
                ByteArrayOutputStream bos = new ByteArrayOutputStream();
                byte[] buf = new byte[4096];
                int n;
                while ((n = randomAccessFile.read(buf)) != -1) {
                    bos.write(buf, 0, n);
                }
                String text = new String(bos.toByteArray(), UTF8);
                // 从中间截断可能落在多字节字符中间，丢弃首个不完整行
                if (start > 0) {
                    int nl = text.indexOf('\n');
                    if (nl >= 0) {
                        text = text.substring(nl + 1);
                    }
                }
                return text;
            } catch (Exception e) {
                e.printStackTrace();
            } finally {
                close(randomAccessFile);
            }
        }
        return "";
    }

    public static boolean clearLogTxt(String txtPath) {
        File file = new File(txtPath);
        File fileBak = new File(txtPath + ".bak");
        if (file.exists()) {
            if (fileBak.exists()) {
                fileBak.delete();
            }
            try {
                file.renameTo(fileBak);
                return file.createNewFile();
            } catch (IOException e) {
                e.printStackTrace();
            }
        } else {
            try {
                File parent = file.getParentFile();
                if (parent != null && !parent.exists()) {
                    parent.mkdirs();
                }
                return file.createNewFile();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        return false;
    }

    public static void close(Closeable closeable) {
        try {
            if (null != closeable) {
                closeable.close();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
