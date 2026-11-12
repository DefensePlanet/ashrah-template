# /capsules - List Catalyst Capsules

List all capsules in the Catalyst system with their status.

## Action

Run this command and display the results:

```bash
echo ""; for capsule in $(ls -d {{CATALYST_ROOT}}/capsules/*/ 2>/dev/null | xargs -I{} basename {} | sort); do
  spec="{{CATALYST_ROOT}}/capsules/$capsule/specs/current.yaml"
  status=$(grep "^status:" "$spec" 2>/dev/null | awk '{print $2}' || echo "?")
  printf "  %-30s %s\n" "$capsule" "[$status]"
done; echo ""; echo "Total: $(ls -d {{CATALYST_ROOT}}/capsules/*/ 2>/dev/null | wc -l | tr -d ' ') capsules"
```
