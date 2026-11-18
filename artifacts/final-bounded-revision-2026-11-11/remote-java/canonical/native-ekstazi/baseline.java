package lab;
public final class ExpiryGate {
    public static final String PAD = "0000000000000000";
    private ExpiryGate() {}
    public static boolean accept(int issued, int now, int maxAge) {
        return (now - issued) <= maxAge;
    }
}
